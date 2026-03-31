"""Channel mixer — continuous HLS stream via ffmpeg concat demuxer.

The :class:`ChannelMixer` runs in a background thread and produces a
continuous HLS live stream by **pre-transcoding** videos into a uniform
format and feeding them to a **single** ffmpeg process via the
**concat demuxer**.

Architecture (2026-03-25 rewrite)
---------------------------------
**Problem with the old approach:** Each video/filler got its own ffmpeg
process.  Process transitions created unavoidable gaps — hls.js would
request segments that didn't exist yet → 404 errors.  Multiple workarounds
(segment counter sync, manifest cleanup, server-side filtering) could not
fix the fundamental issue.

**New approach — concat demuxer + pre-transcode:**

1. All videos for a *block* (a slot or filler period) are **pre-transcoded**
   to a uniform MP4 format (H.264/AAC, 1280×720, 25fps) in a temp
   directory (``.hometools-cache/channel/tmp/``).
2. A **concat list file** (``concat.txt``) is generated listing all
   prepared files in order.
3. A **single** ffmpeg process reads the concat file and outputs a
   continuous HLS stream — no process gaps, no race conditions.
4. Temporary files are **deleted** after playback.

**Design rule:** Streams must be prepared (pre-transcoded) before being
fed into the HLS pipeline.  Live transcoding from disk/NAS into the stream
is prohibited — it leads to inconsistent timing and race conditions.

The HLS manifest (``channel.m3u8``) and segments (``channel_*.ts``) are
written to the HLS output directory and served by the FastAPI server.
"""

from __future__ import annotations

import contextlib
import logging
import subprocess
import threading
import time as _time
from datetime import datetime
from pathlib import Path
from typing import Any

from hometools.streaming.channel.schedule import (
    ResolvedSlot,
    get_display_schedule,
    get_fill_series,
    get_video_duration,
    parse_schedule_file,
    resolve_next_episode,
    resolve_schedule,
)
from hometools.streaming.channel.transcode import (
    build_concat_file,
    cleanup_prepared,
    cleanup_tmp_dir,
    prepare_testcard,
    prepare_video,
)

logger = logging.getLogger(__name__)


class ChannelMixer:
    """Manages the continuous HLS stream generation via concat demuxer.

    Call :meth:`start` to launch the background thread.
    Call :meth:`stop` to terminate gracefully.

    Architecture
    ------------
    Each *block* (a slot or filler period) is handled as follows:

    1. Pre-transcode all videos for the block → uniform MP4 files in tmp/.
    2. Write a concat list file (``concat.txt``).
    3. Start **one** ffmpeg process: ``-f concat → -f hls``.
    4. Wait for the process to finish (or interrupt on stop/slot change).
    5. Delete temporary files.

    This eliminates the process-gap problem entirely — the concat demuxer
    reads file after file without restarting ffmpeg.
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
        hls_list_size: int = 5,
        channel_name: str = "Haus-TV",
        tmp_dir: Path | None = None,
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

        # Temp directory for pre-transcoded files
        if tmp_dir is not None:
            self._tmp_dir = tmp_dir
        else:
            from hometools.config import get_channel_tmp_dir

            self._tmp_dir = get_channel_tmp_dir()

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
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

        # Purge leftover HLS files from previous runs
        self._purge_hls_dir()
        # Clean up any leftover pre-transcoded files
        removed = cleanup_tmp_dir(self._tmp_dir)
        if removed:
            logger.info("Cleaned up %d leftover tmp files", removed)

        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="channel-mixer")
        self._thread.start()
        logger.info("ChannelMixer started (hls_dir=%s, tmp_dir=%s)", self._hls_dir, self._tmp_dir)

    def stop(self) -> None:
        """Stop the mixer gracefully."""
        self._stop_event.set()
        self._kill_current_proc()
        if self._thread is not None:
            self._thread.join(timeout=10)
        # Clean up temp files on shutdown
        cleanup_tmp_dir(self._tmp_dir)
        logger.info("ChannelMixer stopped")

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _purge_hls_dir(self) -> None:
        """Remove all HLS files from a previous run.

        Ensures the mixer starts with a clean slate and the manifest
        never references stale segments from a prior server session.
        """
        removed = 0
        for p in self._hls_dir.glob("channel*"):
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
        # Also remove concat list files
        for p in self._hls_dir.glob("concat*.txt"):
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
        if removed:
            logger.info("Purged %d leftover HLS files from previous run", removed)

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

        If no slot is upcoming today, returns 300 (5 minutes).
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
            return min(min_gap, 300.0)
        return 300.0

    def _run_loop(self) -> None:
        """Main mixer loop — runs until stopped."""
        logger.info("Mixer loop started")

        # Boot testcard — establish the HLS manifest immediately.
        # Without this, the player receives 503 errors for minutes while
        # the mixer pre-transcodes the first real content.  A short testcard
        # (30 s) renders in ~2–3 seconds and creates the manifest instantly.
        # After the boot testcard, hls.js has segments to hold onto while
        # the first real pre-transcode runs.
        if not self._stop_event.is_set():
            self._play_boot_testcard()

        while not self._stop_event.is_set():
            try:
                self._run_one_cycle()
            except Exception:
                logger.error("Mixer cycle error", exc_info=True)
                if self._stop_event.wait(5):
                    break

        logger.info("Mixer loop exiting")

    def _play_boot_testcard(self) -> None:
        """Stream a short boot testcard to establish the HLS manifest.

        The boot testcard is a 30-second SMPTE test pattern that renders
        in ~2–3 seconds (synthetic ffmpeg source → fast).  It creates the
        initial ``channel.m3u8`` manifest and HLS segments so the player
        can connect immediately instead of receiving 503 errors while the
        first real content is being pre-transcoded (which can take minutes
        for long episodes from a NAS).

        After the boot testcard finishes, the old segments remain on disk
        (``cleanup_segments`` has a 600 s retention) and the manifest stays
        valid — hls.js can ride through the brief gap until the first real
        block starts producing new segments.
        """
        logger.info("Playing boot testcard to establish HLS manifest")
        self._play_testcard_block(30.0)

    def _run_one_cycle(self) -> None:
        """Execute one schedule cycle: resolve, pre-transcode, stream block."""
        now = datetime.now()
        schedule_data = parse_schedule_file(self._schedule_file)
        if not schedule_data:
            logger.warning("No schedule data — playing testcard for 60s")
            self._play_testcard_block(60.0)
            return

        # Always update EPG with today's full program (no state changes)
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
            # No scheduled content — try fill programming
            fill_series = get_fill_series(schedule_data)
            if fill_series:
                self._play_fill_block(fill_series)
            else:
                filler_secs = self._seconds_until_next_slot(schedule_data, now)
                logger.info("No scheduled slots — playing testcard for %.0fs", filler_secs)
                self._play_testcard_block(filler_secs)
            return

        # Merge resolved episode info into EPG
        with self._state_lock:
            resolved_map = {r.series_folder: r for r in resolved}
            for entry in self._schedule_cache:
                r = resolved_map.get(entry["series"])
                if r is not None:
                    entry["episode"] = r.episode_title
                    entry["end"] = r.end_dt.isoformat()

        for slot in resolved:
            if self._stop_event.is_set():
                break

            now = datetime.now()

            # If the slot hasn't started yet, fill the gap
            if slot.start_dt > now:
                gap = (slot.start_dt - now).total_seconds()
                if gap > 2:
                    logger.info("Filling gap of %.0fs before %s", gap, slot.series_folder)
                    self._play_gap_block(gap)

                    if self._stop_event.is_set():
                        break
                    now = datetime.now()

            # Calculate seek offset if joining mid-episode
            offset = 0.0
            if now > slot.start_dt:
                offset = (now - slot.start_dt).total_seconds()

            remaining = (slot.end_dt - now).total_seconds()
            if remaining <= 0:
                continue  # Slot already passed

            self._play_slot_block(slot, seek_offset=offset, max_duration=remaining)

        # After all resolved slots, fill until next cycle
        if not self._stop_event.is_set():
            self._play_testcard_block(60.0)

    # -- Block playback (pre-transcode + concat stream) --------------------

    def _play_slot_block(
        self,
        slot: ResolvedSlot,
        *,
        seek_offset: float = 0,
        max_duration: float | None = None,
    ) -> None:
        """Pre-transcode and stream a scheduled video slot."""
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

        # Pre-transcode the video
        prepared = prepare_video(
            slot.video_path,
            self._tmp_dir,
            encoder=self._encoder,
            seek=seek_offset,
            duration=max_duration,
        )
        if prepared is None:
            logger.error("Failed to prepare %s — showing testcard", slot.episode_title)
            self._play_testcard_block(max_duration or 60.0)
            return

        # Stream as a single-file concat block
        prepared_files = [prepared]
        try:
            self._stream_concat_block(prepared_files, label=f"{slot.series_folder}/{slot.episode_title}")
        finally:
            cleanup_prepared(*prepared_files)

    def _play_gap_block(self, duration: float) -> None:
        """Fill a gap before a scheduled slot with filler or testcard."""
        if duration <= 0:
            return

        from hometools.streaming.channel.filler import scan_filler_dir, select_filler

        filler_files = scan_filler_dir(self._filler_dir)
        if not filler_files:
            self._play_testcard_block(duration)
            return

        selected = select_filler(filler_files, duration)
        if not selected:
            self._play_testcard_block(duration)
            return

        with self._state_lock:
            self._now_playing = {
                "series": "Filler",
                "episode": "Zwischenprogramm",
                "is_filler": True,
            }

        # Pre-transcode filler clips, trimming to fit the gap
        prepared_files: list[Path] = []
        remaining = duration
        for clip in selected:
            if self._stop_event.is_set() or remaining <= 1:
                break
            clip_dur = get_video_duration(clip)
            if clip_dur <= 0:
                clip_dur = 60.0
            play_dur = min(clip_dur, remaining)

            p = prepare_video(clip, self._tmp_dir, encoder=self._encoder, duration=play_dur)
            if p is not None:
                prepared_files.append(p)
                remaining -= play_dur

        if not prepared_files:
            self._play_testcard_block(duration)
            return

        try:
            self._stream_concat_block(prepared_files, label="filler-gap")
        finally:
            cleanup_prepared(*prepared_files)

    def _play_fill_block(self, fill_series: list[str]) -> None:
        """Play one random episode from fill_series as background programming."""
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
                duration = 1800.0

            logger.info("Fill programming: %s / %s (%.0fs)", series, episode.name, duration)

            with self._state_lock:
                self._now_playing = {
                    "series": series,
                    "episode": episode.stem,
                    "file": str(episode),
                    "is_filler": True,
                }

            prepared = prepare_video(episode, self._tmp_dir, encoder=self._encoder)
            if prepared is None:
                logger.warning("Failed to prepare fill episode %s — trying next", episode.name)
                continue

            try:
                self._stream_concat_block([prepared], label=f"fill/{series}/{episode.name}")
            finally:
                cleanup_prepared(prepared)
            return

        # None of the fill_series produced an episode — fallback
        logger.warning("No fill episodes resolved — showing test card")
        self._play_testcard_block(300.0)

    def _play_testcard_block(self, duration: float) -> None:
        """Pre-render and stream a test card (Sendepause)."""
        if duration <= 0:
            return

        with self._state_lock:
            self._now_playing = {
                "series": "Sendepause",
                "episode": "Testbild",
                "is_filler": True,
            }

        prepared = prepare_testcard(
            duration,
            self._tmp_dir,
            channel_name=self._channel_name,
            encoder=self._encoder,
        )
        if prepared is None:
            logger.error("Failed to render testcard — sleeping %.0fs", duration)
            self._stop_event.wait(min(duration, 30))
            return

        try:
            self._stream_concat_block([prepared], label="testcard")
        finally:
            cleanup_prepared(prepared)

    # -- Core streaming via concat demuxer ---------------------------------

    def _stream_concat_block(self, prepared_files: list[Path], *, label: str = "") -> None:
        """Run a single ffmpeg process with concat demuxer → HLS output.

        This is the **only** place where ffmpeg is started for streaming.
        All input files must be pre-transcoded to the uniform target format.

        The concat demuxer reads files sequentially without restarting
        ffmpeg — producing a gap-free stream.
        """
        if not prepared_files:
            return

        concat_file = self._hls_dir / "concat.txt"
        build_concat_file(prepared_files, concat_file)

        manifest = self._hls_dir / "channel.m3u8"
        segment_pattern = str(self._hls_dir / "channel_%05d.ts")

        cmd = [
            "ffmpeg",
            "-y",
            # Concat demuxer input
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            # Since files are already pre-transcoded to the target format,
            # we can copy codecs (no re-encoding!) — this is nearly instant.
            "-c",
            "copy",
            # HLS output
            "-f",
            "hls",
            "-hls_time",
            str(self._hls_time),
            "-hls_list_size",
            str(self._hls_list_size),
            "-hls_segment_filename",
            segment_pattern,
            "-v",
            "warning",
            str(manifest),
        ]

        logger.info("Starting concat stream for %s (%d files)", label, len(prepared_files))
        logger.debug("ffmpeg concat command: %s", " ".join(cmd))

        proc: subprocess.Popen | None = None
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            with self._proc_lock:
                self._current_proc = proc

            # Wait for process, doing periodic segment cleanup
            cleanup_tick = 0
            while proc.poll() is None:
                if self._stop_event.wait(0.5):
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=3)
                    break
                cleanup_tick += 1
                if cleanup_tick >= 60:  # every ~30s
                    self.cleanup_segments()
                    cleanup_tick = 0

            if proc.returncode and proc.returncode != 0 and not self._stop_event.is_set():
                stderr_out = b""
                if proc.stderr:
                    stderr_out = proc.stderr.read(500)
                logger.warning(
                    "ffmpeg concat exited with code %d for %s: %s",
                    proc.returncode,
                    label,
                    stderr_out.decode("utf-8", errors="replace")[:300] if isinstance(stderr_out, bytes) else str(stderr_out)[:300],
                )

        except FileNotFoundError:
            logger.error("ffmpeg not found — channel mixer requires ffmpeg on PATH")
            self._stop_event.wait(10)
        except Exception:
            logger.error("ffmpeg concat error for %s", label, exc_info=True)
        finally:
            with self._proc_lock:
                self._current_proc = None
            if proc is not None:
                if proc.stderr:
                    proc.stderr.close()
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=3)

        # Clean up concat file
        with contextlib.suppress(OSError):
            concat_file.unlink(missing_ok=True)

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

    def cleanup_segments(self, *, max_age_seconds: int = 600) -> int:
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
