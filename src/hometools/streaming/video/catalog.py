"""Catalog helpers for the video streaming prototype.

Built on top of :mod:`hometools.streaming.core` — same query/sort/filter
logic as the audio streaming component.

INSTRUCTIONS (local):
- ``_title_from_filename`` strips codec/resolution tags. Keep the regex list
  updated when new common tags appear. Test via ``test_streaming_video.py``.
- ``_folder_as_artist`` uses the first subfolder as category. Videos at the
  library root get ``artist=""``.
- Default sort is **title** (not artist) because video folders are less
  meaningful than music artists.
- Thumbnail lookups are **non-blocking**: ``build_video_index`` only checks
  the on-disk cache.  Background generation is triggered separately via
  ``start_background_thumbnail_generation(collect_thumbnail_work(...))``.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from hometools.constants import VIDEO_SUFFIX
from hometools.streaming.core.catalog import list_artists, parse_season_episode
from hometools.streaming.core.catalog import query_items as query_videos
from hometools.streaming.core.catalog import sort_items as sort_videos
from hometools.streaming.core.media_overrides import apply_overrides
from hometools.streaming.core.models import MediaItem, encode_relative_path
from hometools.streaming.core.server_utils import safe_resolve
from hometools.streaming.core.thumbnailer import check_thumbnail_cached
from hometools.utils import get_files_in_folder

logger = logging.getLogger(__name__)

_METADATA_CACHE_FILE = "video_metadata_cache.json"

__all__ = [
    "MediaItem",
    "build_video_index",
    "collect_thumbnail_work",
    "encode_relative_path",
    "list_artists",
    "query_videos",
    "sort_videos",
]


def _title_from_filename(stem: str) -> str:
    """Extract a human-readable title from a video filename stem.

    Strips common codec / resolution tags and normalises separators.
    """
    # Replace dots and underscores used as word separators
    title = re.sub(r"[._]", " ", stem)
    # Strip resolution, codec, source tags
    title = re.sub(r"\b(1080|720|480|2160|4k)p?\b", "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"\b(x264|x265|h\.?264|h\.?265|hevc|avc|BluRay|BDRip|WEBRip|WEB-DL|HDRip|DVDRip|DD5\.?1|AAC|DTS)\b",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\[.*?]", "", title)
    title = re.sub(r"\(.*?\)", "", title)
    # Collapse whitespace
    title = re.sub(r"\s{2,}", " ", title).strip()
    return title or stem


def _folder_as_artist(file_path: Path, library_root: Path) -> str:
    """Use the first directory level below the library root as 'artist' (folder name)."""
    try:
        relative = safe_resolve(file_path).relative_to(safe_resolve(library_root))
        parts = relative.parts
        if len(parts) > 1:
            return parts[0]
    except ValueError:
        pass
    return ""


def _read_metadata_fast(p: Path) -> dict[str, str] | None:
    """Read embedded metadata using mutagen only — no ffprobe subprocess.

    This is used during index building where speed matters more than
    completeness.  The full ``read_embedded_metadata`` (with ffprobe
    fallback) is reserved for single-track metadata refresh requests.
    """
    from mutagen import File

    from hometools.audio.metadata import _find_tag

    try:
        audio = File(p)
        if audio is not None and audio.tags:
            title = _find_tag(
                audio.tags,
                "\xa9nam",
                "title",
                "TITLE",
                "TIT2",
                "Title",
            )
            artist = _find_tag(
                audio.tags,
                "\xa9ART",
                "artist",
                "ARTIST",
                "TPE1",
                "Author",
            )
            if title or artist:
                return {"title": title, "artist": artist}
    except Exception:
        pass
    return None


def _metadata_cache_path(cache_dir: Path) -> Path:
    """Return the on-disk metadata cache path inside the shadow cache."""
    return cache_dir / _METADATA_CACHE_FILE


def _load_metadata_cache(cache_dir: Path) -> dict[str, dict[str, object]]:
    """Load the persistent metadata cache from disk.

    Returns an empty dict on any error or schema mismatch.
    """
    try:
        path = _metadata_cache_path(cache_dir)
        if not path.exists():
            return {}
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("items"), dict):
            return raw["items"]
        if isinstance(raw, dict):
            return raw
    except Exception:
        logger.debug("Could not load video metadata cache from %s", cache_dir, exc_info=True)
    return {}


def _save_metadata_cache(cache_dir: Path, cache: dict[str, dict[str, object]]) -> None:
    """Persist the metadata cache to disk.  Never raises."""
    try:
        path = _metadata_cache_path(cache_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "items": cache}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.debug("Could not save video metadata cache to %s", cache_dir, exc_info=True)


def _file_signature(p: Path) -> tuple[int, int]:
    """Return a stable file signature based on mtime and size."""
    try:
        stat = p.stat()
        return getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)), stat.st_size
    except OSError:
        return 0, 0


def build_video_index(library_dir: Path, *, cache_dir: Path | None = None) -> list[MediaItem]:
    """Build a read-only video index from a local video library.

    Thumbnail URLs are only included when a cached thumbnail already exists
    on disk — no extraction is attempted here so startup stays fast.

    Uses mutagen-only metadata reading (no ffprobe subprocess) to avoid
    blocking for minutes on large libraries.
    """
    if not library_dir.exists() or not library_dir.is_dir():
        return []

    t0 = time.monotonic()
    root = safe_resolve(library_dir)
    scan_t0 = time.monotonic()
    video_files = get_files_in_folder(root, suffix_accepted=VIDEO_SUFFIX)
    scan_elapsed = time.monotonic() - scan_t0
    items: list[MediaItem] = []
    meta_hits = 0
    metadata_cache = _load_metadata_cache(cache_dir) if cache_dir is not None else {}
    metadata_cache_loaded = len(metadata_cache)
    metadata_cache_dirty = False
    metadata_cache_hits = 0
    metadata_cache_misses = 0
    stale_cache_entries = 0
    mutagen_reads = 0
    seen_relative_paths: set[str] = set()

    logger.info(
        "Building video index for %s — %d files discovered in %.2fs",
        root,
        len(video_files),
        scan_elapsed,
    )

    for video_file in video_files:
        relative_path = safe_resolve(video_file).relative_to(root).as_posix()
        seen_relative_paths.add(relative_path)

        meta = None
        if cache_dir is not None:
            sig_mtime_ns, sig_size = _file_signature(video_file)
            cached = metadata_cache.get(relative_path)
            if isinstance(cached, dict) and cached.get("mtime_ns") == sig_mtime_ns and cached.get("size") == sig_size:
                metadata_cache_hits += 1
                cached_title = str(cached.get("title") or "")
                cached_artist = str(cached.get("artist") or "")
                if cached_title or cached_artist:
                    meta = {"title": cached_title, "artist": cached_artist}
            else:
                metadata_cache_misses += 1
                mutagen_reads += 1
                meta = _read_metadata_fast(video_file)
                metadata_cache[relative_path] = {
                    "mtime_ns": sig_mtime_ns,
                    "size": sig_size,
                    "title": meta.get("title", "") if meta else "",
                    "artist": meta.get("artist", "") if meta else "",
                }
                metadata_cache_dirty = True
        else:
            mutagen_reads += 1
            meta = _read_metadata_fast(video_file)

        meta_title = str(meta.get("title") or "") if meta else ""
        if meta_title.strip():
            title = meta_title.strip()
            meta_hits += 1
        else:
            title = _title_from_filename(video_file.stem)

        meta_artist = str(meta.get("artist") or "") if meta else ""
        if meta_artist.strip():
            folder = meta_artist.strip()
        else:
            folder = _folder_as_artist(video_file, root)

        thumbnail_url = ""
        if cache_dir is not None:
            thumb = check_thumbnail_cached(cache_dir, "video", relative_path)
            if thumb is not None:
                thumbnail_url = f"/thumb?path={encode_relative_path(relative_path)}"

        season, episode = parse_season_episode(video_file.name)

        items.append(
            MediaItem(
                relative_path=relative_path,
                title=title,
                artist=folder,
                stream_url=f"/video/stream?path={encode_relative_path(relative_path)}",
                media_type="video",
                thumbnail_url=thumbnail_url,
                season=season,
                episode=episode,
            )
        )

    if cache_dir is not None:
        stale_keys = [key for key in metadata_cache if key not in seen_relative_paths]
        if stale_keys:
            stale_cache_entries = len(stale_keys)
            for key in stale_keys:
                metadata_cache.pop(key, None)
            metadata_cache_dirty = True
        if metadata_cache_dirty:
            save_t0 = time.monotonic()
            _save_metadata_cache(cache_dir, metadata_cache)
            logger.info(
                "Video metadata cache updated: %d entries written to %s in %.2fs",
                len(metadata_cache),
                _metadata_cache_path(cache_dir),
                time.monotonic() - save_t0,
            )
        logger.info(
            "Video metadata cache stats: loaded=%d hits=%d misses=%d stale_removed=%d mutagen_reads=%d",
            metadata_cache_loaded,
            metadata_cache_hits,
            metadata_cache_misses,
            stale_cache_entries,
            mutagen_reads,
        )

    elapsed = time.monotonic() - t0
    logger.info(
        "Video index built: %d items (%d with embedded metadata) in %.1fs [scan=%.2fs, mutagen_reads=%d, cache_hits=%d, cache_misses=%d]",
        len(items),
        meta_hits,
        elapsed,
        scan_elapsed,
        mutagen_reads,
        metadata_cache_hits,
        metadata_cache_misses,
    )

    # Apply per-folder YAML overrides (title, season, episode, series_title)
    items = apply_overrides(items, root)

    return sort_videos(items, sort_by="title")


def collect_thumbnail_work(
    library_dir: Path,
    cache_dir: Path,
) -> list[tuple[Path, Path, str, str]]:
    """Return a list of ``(media_path, cache_dir, media_type, relative_path)``
    tuples for all video files in the library — ready for
    :func:`~hometools.streaming.core.thumbnailer.start_background_thumbnail_generation`.
    """
    if not library_dir.exists() or not library_dir.is_dir():
        return []

    root = safe_resolve(library_dir)
    work: list[tuple[Path, Path, str, str]] = []

    for video_file in get_files_in_folder(root, suffix_accepted=VIDEO_SUFFIX):
        relative_path = safe_resolve(video_file).relative_to(root).as_posix()
        work.append((video_file, cache_dir, "video", relative_path))

    return work
