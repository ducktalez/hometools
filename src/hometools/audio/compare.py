"""Audio file comparison, duplicate detection, and batch sanitization."""

import inspect
import logging
from pathlib import Path

import yaml

from hometools.audio.metadata import _open_audio, audiofile_assume_artist_title
from hometools.audio.sanitize import sanitize_track_to_path, stem_identifier
from hometools.constants import AUDIO_LOSSLESS_SUFFIX, AUDIO_LOSS_SUFFIX, MEDIAINFO_DEL_KEYS
from hometools.print_tools import highlight_removed
from hometools.utils import (
    deleting_file,
    get_audio_files_in_folder,
    get_file_size,
    get_files_in_folder,
    rename_path,
    user_rename_file,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# YAML look-up table helpers
# ---------------------------------------------------------------------------


def yaml_load(p: Path) -> dict:
    """Load a YAML file, returning an empty dict on missing file."""
    try:
        with p.open("r", encoding="utf-8") as fh:
            return yaml.load(fh, Loader=yaml.FullLoader) or {}
    except FileNotFoundError:
        logger.warning(f"YAML file not found: {p}")
        return {}


def yaml_dump(p: Path, data):
    """Dump *data* to a YAML file."""
    with p.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh, allow_unicode=True)


def strip_mediainfo_keys(data: dict) -> dict:
    """Remove verbose mediainfo keys from every entry in *data*."""
    for v in data.values():
        for key in MEDIAINFO_DEL_KEYS:
            v.pop(key, None)
    return data


# ---------------------------------------------------------------------------
# Track listing & sanitization
# ---------------------------------------------------------------------------


def get_all_tracks(p: Path) -> list[Path]:
    """Return all audio file paths under *p*."""
    return get_audio_files_in_folder(p)


def sanitize_all_track_names_batch(directory: Path):
    """Preview & batch-rename tracks with sanitized stems."""
    logger.info(f"Starting: {inspect.currentframe().f_code.co_name}")
    tracks = get_all_tracks(directory)
    changes: dict[Path, Path] = {}

    print(f"{'Original Name':60} -> {'Sanitized Name'}")
    print("=" * 100)

    for p in tracks:
        history = stem_identifier(p.stem)
        sanitized = history[-1]
        if sanitized != p.stem:
            new_path = p.parent / f"{sanitized}{p.suffix}"
            changes[p] = new_path
            print(f"{highlight_removed(p.stem, sanitized)} ->\n{sanitized}")

    if not changes:
        print("✅ No changes needed.")
        return

    print("\nPreview complete.")
    answer = input('Apply changes? Type "all" to rename everything, anything else to cancel.\n> ')
    if answer.strip().lower() == "all":
        for old, new in changes.items():
            try:
                rename_path(old, new)
                print(f"✅ Renamed: {old.name} → {new.name}")
            except FileExistsError:
                print(f"❗ Already exists: {new.name} — skipped.")
    else:
        print("❌ No changes applied.")


def sanitize_all_track_names(directory: Path):
    """Interactively sanitize track names one-by-one."""
    logger.info(f"Starting: {inspect.currentframe().f_code.co_name}")
    tracks = get_all_tracks(directory)
    changes: dict[Path, Path] = {}

    for p in tracks:
        sanitized = sanitize_track_to_path(p.stem)[-1]
        if sanitized != p.stem:
            print(f"{highlight_removed(p.stem, sanitized)}{p.suffix}")
            print(f"{sanitized}{p.suffix}")
            changes[p] = p.parent / f"{sanitized}{p.suffix}"

    answer = input(
        'Sanitize track names? Type "all" to apply all at once,\n'
        "press Enter to decide for each.\n"
    )
    for old, new in changes.items():
        try:
            if answer == "all":
                rename_path(old, new)
                continue
            ok = input(f"{highlight_removed(old.name, new.name)} ->\n{new.name}")
            if ok == "":
                rename_path(old, new)
        except FileExistsError:
            logger.warning(f"FileExistsError: {old} -> {new}")


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def get_audio_dict(p: Path, suffix=None, key="path") -> dict:
    """Build a dict of audio file metadata keyed by *key*."""
    result = {}
    for pp in get_files_in_folder(p, suffix_accepted=suffix):
        artist_f, title_f = audiofile_assume_artist_title(pp)
        try:
            audio = _open_audio(pp)
            tags = audio.tags or {}
            title = tags.get("title", ["Unknown"])[0]
            artist = tags.get("artist", ["Unknown"])[0]
            album = tags.get("album", ["Unknown"])[0]
            stem = stem_identifier(pp.name)[-1]

            values = {
                "path": pp,
                "stem": stem,
                "suffix": pp.suffix,
                "size": get_file_size(pp),
                "title": title,
                "artist": artist,
                "album": album,
                "artist-path": artist_f,
                "title-path": title_f,
            }
            result[values[key]] = values
        except Exception as e:
            logger.error(f"Error reading {pp}: {e}")
    return result


def check_audioformat_duplicates(p: Path):
    """Report lossless files that have no lossy counterpart."""
    logger.info(f"Starting: {inspect.currentframe().f_code.co_name}")
    wav_d = get_audio_dict(p, suffix=AUDIO_LOSSLESS_SUFFIX, key="stem")
    mp3_d = get_audio_dict(p, suffix=AUDIO_LOSS_SUFFIX, key="stem")

    missing = [v["path"] for k, v in wav_d.items() if k not in mp3_d]
    if missing:
        print("Lossless files without a lossy counterpart:")
        for m in missing:
            print(f"  {m}")
    return missing


def delete_song_dupes(main_dir: Path, new_dir: Path, check_file_size=False, dry_run=True):
    """Delete tracks in *new_dir* that already exist in *main_dir*."""
    logger.info(f"Starting: {inspect.currentframe().f_code.co_name}")
    main_tracks = {stem_identifier(p.name)[-1]: p for p in get_audio_files_in_folder(main_dir)}
    new_tracks = {stem_identifier(p.name)[-1]: p for p in get_audio_files_in_folder(new_dir)}

    duplicates = set(main_tracks) & set(new_tracks)

    if check_file_size:
        size_mismatch = {
            t for t in duplicates
            if get_file_size(main_tracks[t]) != get_file_size(new_tracks[t])
        }
        duplicates -= size_mismatch
        if size_mismatch:
            logger.warning(f"Ignoring {len(size_mismatch)} duplicates with different sizes.")

    print("Found duplicates:")
    for d in duplicates:
        print(f"  - {new_tracks[d]}")

    if not dry_run:
        for d in duplicates:
            try:
                new_tracks[d].unlink()
                logger.info(f"Deleted duplicate: {new_tracks[d]}")
            except Exception as e:
                logger.error(f"Failed to delete {new_tracks[d]}: {e}")


def find_all_dupes(directory: Path, delete_dupes=False):
    """Find duplicate audio files by stem name across sub-folders."""
    logger.info(f"Starting: {inspect.currentframe().f_code.co_name}")
    tracks = get_all_tracks(directory)
    dupes: dict[str, list] = {}

    for p in tracks:
        dupes.setdefault(p.stem, []).append({"path": p, "size": get_file_size(p)})

    dupes = {k: v for k, v in dupes.items() if len(v) > 1}

    if delete_dupes:
        for k, v in dupes.items():
            v = sorted(v, key=lambda x: x["size"], reverse=True)
            to_delete = v[1:]
            kept = v[0]
            info = "\n".join(f'{x["path"]} ({x["size"]})' for x in to_delete)
            print(f'Keeping: {kept["path"]} (size {kept["size"]})\nRemoving:\n{info}')
            for x in to_delete:
                deleting_file(x["path"])
    else:
        for k, v in dupes.items():
            print(f"Duplicate: {k} ({len(v)}x)")
    return dupes


def remove_album_in_pathname(directory: Path):
    """Remove redundant album name from file names (e.g. 'Artist - Title - Album.mp3')."""
    logger.info(f"Starting: {inspect.currentframe().f_code.co_name}")
    tracks = get_all_tracks(directory)

    for p in tracks:
        try:
            audio = _open_audio(p)
            tags = audio.tags or {}
            title = tags.get("title", [None])[0] or "Unknown"
            artist = tags.get("artist", [None])[0] or "Unknown"
            album = tags.get("album", [None])[0] or "Unknown"

            bad_stem = sanitize_track_to_path(f"{artist} - {title} - {album}")[-1]
            correct_stem = sanitize_track_to_path(f"{artist} - {title}")[-1]

            if p.stem == bad_stem:
                new_path = p.with_name(f"{correct_stem}{p.suffix}")
                user_rename_file(p, new_path)
                logger.info(f"Renamed: {p.name} -> {new_path.name}")
        except Exception as e:
            logger.error(f"Error processing {p}: {e}")
