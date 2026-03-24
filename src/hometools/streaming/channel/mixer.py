"""Channel mixer — continuous HLS stream via ffmpeg.

The :class:`ChannelMixer` runs in a background thread and produces a
continuous HLS live stream by piping scheduled videos (and filler content
for gaps) through ffmpeg.  Each program slot gets its own ffmpeg process
with ``-f hls`` output; ``hls_flags=append_list`` ensures seamless
continuity across process restarts.

The HLS manifest (``channel.m3u8``) and segments (``channel_*.ts``) are
written to the HLS output directory and served by the FastAPI server.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time as _time
from datetime import datetime
from pathlib import Path
from typing import Any

from hometools.streaming.channel.filler import (
    generate_testcard_filler_args,
    scan_filler_dir,
    select_filler,
)
from hometools.streaming.channel.schedule import (
    ResolvedSlot,
    get_display_schedule,
    get_fill_series,
    get_video_duration,
    parse_schedule_file,
    resolve_next_episode,
    resolve_schedule,
)

logger = logging.getLogger(__name__)

# Monotonically increasing segment counter across ffmpeg restarts
_segment_counter_lock = threading.Lock()
_segment_counter: int = 0


def _next_segment_start() -> int:
    """Return the current segment counter (thread-safe)."""
    with _segment_counter_lock:
        return _segment_counter


def _advance_segment_counter(count: int) -> None:
    """Advance the global segment counter by *count*."""
    global _segment_counter
    with _segment_counter_lock:
        _segment_counter += count


class ChannelMixer:
    """Manages the continuous HLS stream generation.

    Call :meth:`start` to launch the background thread.
    Call :meth:`stop` to terminate gracefully.
    """

    def __init__(
        self,
        schedule_file: Path,
        library_dir: Path,
        filler_dir: Path,
        hls_dir: Path,
        state_dir: Path,
        *,
        encoder: str = "libx264",
        hls_time: int = 6,
        hls_list_size: int = 10,
        channel_name: str = "Haus-TV",
    ) -> None:
        self._schedule_file = schedule_file
        self._library_dir = library_dir
        self._filler_dir = filler_dir
        self._hls_dir = hls_dir
        self._state_dir = state_dir
        self._encoder = encoder
        self._hls_time = hls_time
        self._hls_list_size = hls_list_size
        self._channel_name = channel_name

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._current_proc: subprocess.Popen | None = None
        self._proc_lock = threading.Lock()

        # Current state (read by API endpoints)
        self._now_playing: dict[str, Any] = {}
        self._schedule_cache: list[dict[str, Any]] = []
        self._state_lock = threading.Lock()

    # -- Public API --------------------------------------------------------

    def start(self) -> None:
        """Start the mixer background thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("ChannelMixer already running")
            return

        self._stop_event.clear()
        self._hls_dir.mkdir(parents=True, exist_ok=True)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="channel-mixer")
        self._thread.start()
        logger.info("ChannelMixer started (hls_dir=%s)", self._hls_dir)

    def stop(self) -> None:
        """Stop the mixer gracefully."""
        self._stop_event.set()
        self._kill_current_proc()
        if self._thread is not None:
            self._thread.join(timeout=10)
        logger.info("ChannelMixer stopped")

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_now_playing(self) -> dict[str, Any]:
        """Return info about what's currently playing."""
        with self._state_lock:
            return dict(self._now_playing)

    def get_epg(self) -> list[dict[str, Any]]:
        """Return the upcoming program schedule."""
        with self._state_lock:
            return list(self._schedule_cache)

    # -- Internal ----------------------------------------------------------

    @staticmethod
    def _seconds_until_next_slot(
        schedule_data: dict[str, Any],
        now: datetime,
    ) -> float:
        """Return seconds until the next scheduled slot, capped at 300s.

        If no slot is upcoming today, returns 300 (5 minutes).  This avoids
        the mixer spinning on very short filler cycles while still waking up
        periodically to re-evaluate the schedule.
        """
        from hometools.streaming.channel.schedule import get_slots_for_date

        slots = get_slots_for_date(schedule_data, now)
        today = now.date()
        min_gap: float | None = None

        for slot in slots:
            start_dt = datetime.combine(today, slot.start_time)
            gap = (start_dt - now).total_seconds()
            if gap > 0 and (min_gap is None or gap < min_gap):
                min_gap = gap

        if min_gap is not None:
            # Cap at 300s so we re-check periodically
            return min(min_gap, 300.0)
        return 300.0

    def _run_loop(self) -> None:
        """Main mixer loop — runs until stopped."""
        logger.info("Mixer loop started")

        while not self._stop_event.is_set():
            try:
                self._run_one_cycle()
            except Exception:
                logger.error("Mixer cycle error", exc_info=True)
                if self._stop_event.wait(5):
                    break

        logger.info("Mixer loop exiting")

    def _run_one_cycle(self) -> None:
        """Execute one schedule cycle: resolve schedule, play slots, fill gaps."""
        now = datetime.now()
        schedule_data = parse_schedule_file(self._schedule_file)
        if not schedule_data:
            logger.warning("No schedule data — playing filler for 60s")
            self._play_filler(60.0)
            return

        # Always update the EPG with today's full program (no state changes)
        display = get_display_schedule(schedule_data, now=now)
        with self._state_lock:
            self._schedule_cache = display

        resolved = resolve_schedule(
            schedule_data,
            self._library_dir,
            self._state_dir,
            now=now,
            lookahead_hours=6,
        )

        if not resolved:
            # No scheduled content — try fill programming from fill_series
            fill_series = get_fill_series(schedule_data)
            if fill_series:
                self._play_fill_episode(fill_series)
            else:
                # No fill series configured — show filler/testcard
                filler_secs = self._seconds_until_next_slot(schedule_data, now)
                logger.info(
                    "No scheduled slots and no fill_series — playing filler for %.0fs",
                    filler_secs,
                )
                self._play_filler(filler_secs)
            return

        # Merge resolved episode info into EPG for currently-playing slots
        with self._state_lock:
            resolved_map = {r.series_folder: r for r in resolved}
            for entry in self._schedule_cache:
                r = resolved_map.get(entry["series"])
                if r is not None:
                    entry["episode"] = r.episode_title
                    entry["end"] = r.end_dt.isoformat()

        for _i, slot in enumerate(resolved):
            if self._stop_event.is_set():
                break

            now = datetime.now()

            # If the slot hasn't started yet, fill the gap
            if slot.start_dt > now:
                gap = (slot.start_dt - now).total_seconds()
                if gap > 2:
                    logger.info("Filling gap of %.0fs before %s", gap, slot.series_folder)
                    self._play_filler(gap)

                    if self._stop_event.is_set():
                        break

                    # Re-check time after filler
                    now = datetime.now()

            # Calculate seek offset if we're joining mid-episode
            offset = 0.0
            if now > slot.start_dt:
                offset = (now - slot.start_dt).total_seconds()

            remaining = (slot.end_dt - now).total_seconds()
            if remaining <= 0:
                continue  # Slot already passed

            self._play_slot(slot, seek_offset=offset, max_duration=remaining)

        # After all resolved slots, fill until next cycle
        if not self._stop_event.is_set():
            self._play_filler(60.0)

    def _play_slot(
        self,
        slot: ResolvedSlot,
        *,
        seek_offset: float = 0,
        max_duration: float | None = None,
    ) -> None:
        """Play a scheduled video slot via ffmpeg HLS output."""
        logger.info(
            "Playing: %s / %s (offset=%.0fs, max_dur=%.0fs)",
            slot.series_folder,
            slot.episode_title,
            seek_offset,
            max_duration or 0,
        )

        with self._state_lock:
            self._now_playing = {
                "series": slot.series_folder,
                "episode": slot.episode_title,
                "file": str(slot.video_path),
                "start": slot.start_dt.isoformat(),
                "end": slot.end_dt.isoformat(),
                "is_filler": False,
            }

        input_args = []
        if seek_offset > 1:
            input_args.extend(["-ss", f"{seek_offset:.1f}"])
        input_args.extend(["-i", str(slot.video_path)])
        if max_duration and max_duration > 0:
            input_args.extend(["-t", f"{max_duration:.1f}"])

        self._run_ffmpeg(input_args, label=f"{slot.series_folder}/{slot.episode_title}")

    def _play_filler(self, duration: float) -> None:
        """Play filler content for the given duration."""
        if duration <= 0:
            return

        with self._state_lock:
            self._now_playing = {
                "series": "Filler",
                "episode": "Zwischenprogramm",
                "is_filler": True,
            }

        filler_files = scan_filler_dir(self._filler_dir)
        if not filler_files:
            # No filler files — show TV test card (Testbild) with channel info
            logger.info("No filler files — showing test card (Sendepause) for %.0fs", duration)
            with self._state_lock:
                self._now_playing = {
                    "series": "Sendepause",
                    "episode": "Testbild",
                    "is_filler": True,
                }
            input_args = generate_testcard_filler_args(
                duration,
                channel_name=self._channel_name,
            )
            self._run_ffmpeg(input_args, label="testcard-filler")
            return

        # Play filler clips sequentially until duration is filled
        selected = select_filler(filler_files, duration)
        remaining = duration

        for clip in selected:
            if self._stop_event.is_set() or remaining <= 1:
                break

            clip_dur = get_video_duration(clip)
            if clip_dur <= 0:
                clip_dur = 60.0  # fallback

            play_dur = min(clip_dur, remaining)
            input_args = ["-i", str(clip), "-t", f"{play_dur:.1f}"]

            with self._state_lock:
                self._now_playing = {
                    "series": "Filler",
                    "episode": clip.stem,
                    "is_filler": True,
                }

            self._run_ffmpeg(input_args, label=f"filler/{clip.name}")
            remaining -= play_dur

    def _play_fill_episode(self, fill_series: list[str]) -> None:
        """Play one random episode from *fill_series* as background programming.

        Called when no scheduled slot is active but ``fill_series`` is
        configured in the schedule YAML.  Picks a random series, resolves
        one episode via "random" strategy, and plays it in full.

        Falls back to testcard if no episodes can be resolved.
        """
        import random as _rand

        _rand.shuffle(fill_series)

        for series in fill_series:
            episode = resolve_next_episode(
                self._library_dir,
                series,
                self._state_dir,
                "random",
            )
            if episode is None:
                continue

            duration = get_video_duration(episode)
            if duration <= 0:
                duration = 1800.0  # fallback: 30 min

            logger.info(
                "Fill programming: %s / %s (%.0fs)",
                series,
                episode.name,
                duration,
            )

            with self._state_lock:
                self._now_playing = {
                    "series": series,
                    "episode": episode.stem,
                    "file": str(episode),
                    "is_filler": True,
                }

            input_args = ["-i", str(episode)]
            self._run_ffmpeg(input_args, label=f"fill/{series}/{episode.name}")
            return

        # None of the fill_series produced an episode — fallback to testcard
        logger.warning("No fill episodes resolved — showing test card")
        self._play_filler(300.0)

    def _run_ffmpeg(self, input_args: list[str], *, label: str = "") -> None:
        """Run a single ffmpeg process with HLS output.

        Blocks until the process finishes or :meth:`stop` is called.
        """
        seg_start = _next_segment_start()
        manifest = self._hls_dir / "channel.m3u8"
        segment_pattern = str(self._hls_dir / "channel_%05d.ts")

        cmd = [
            "ffmpeg",
            "-y",
            *input_args,
            "-c:v",
            self._encoder,
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ac",
            "2",
            "-ar",
            "44100",
            # Normalize video to 1280x720 for consistent stream
            "-vf",
            "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-r",
            "25",
            "-f",
            "hls",
            "-hls_time",
            str(self._hls_time),
            "-hls_list_size",
            str(self._hls_list_size),
            "-hls_flags",
            "delete_segments+append_list",
            "-hls_segment_filename",
            segment_pattern,
            "-hls_start_number_source",
            "generic",
            "-start_number",
            str(seg_start),
            "-v",
            "warning",
            str(manifest),
        ]

        logger.debug("ffmpeg command for %s: %s", label, " ".join(cmd))

        proc: subprocess.Popen | None = None
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            with self._proc_lock:
                self._current_proc = proc

            # Wait for process to finish, checking stop event periodically
            while proc.poll() is None:
                if self._stop_event.wait(0.5):
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=3)
                    break

            if proc.returncode and proc.returncode != 0 and not self._stop_event.is_set():
                stderr_out = b""
                if proc.stderr:
                    stderr_out = proc.stderr.read(500)
                logger.warning(
                    "ffmpeg exited with code %d for %s: %s",
                    proc.returncode,
                    label,
                    stderr_out.decode("utf-8", errors="replace")[:300],
                )

            # Count segments produced
            segments = list(self._hls_dir.glob("channel_*.ts"))
            _advance_segment_counter(max(1, len(segments) - seg_start))

        except FileNotFoundError:
            logger.error("ffmpeg not found — channel mixer requires ffmpeg on PATH")
            self._stop_event.wait(10)  # Don't spin
        except Exception:
            logger.error("ffmpeg error for %s", label, exc_info=True)
        finally:
            with self._proc_lock:
                self._current_proc = None
            if proc is not None:
                if proc.stderr:
                    proc.stderr.close()
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=3)

    def _kill_current_proc(self) -> None:
        """Kill the currently running ffmpeg process (if any)."""
        with self._proc_lock:
            proc = self._current_proc
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)

    def cleanup_segments(self, *, max_age_seconds: int = 120) -> int:
        """Remove old HLS segments.  Returns the number of files removed."""
        if not self._hls_dir.exists():
            return 0
        removed = 0
        cutoff = _time.time() - max_age_seconds
        for p in self._hls_dir.glob("channel_*.ts"):
            try:
                if p.stat().st_mtime < cutoff:
                    p.unlink()
                    removed += 1
            except OSError:
                pass
        return removed
