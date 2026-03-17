"""General-purpose file and path utilities for hometools."""

import logging
import os
import re
import subprocess
from pathlib import Path

from hometools.config import get_delete_dir
from hometools.print_tools import Colors

logger = logging.getLogger(__name__)


def run_text_subprocess(*args, **kwargs) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with deterministic Unicode decoding.

    External media tools such as ``ffprobe``/``ffmpeg`` often emit UTF-8 text
    even on Windows systems whose ANSI code page is still CP1252.  Using
    ``text=True`` without an explicit encoding can therefore crash inside the
    stdlib reader thread with ``UnicodeDecodeError``.  Force UTF-8 and replace
    undecodable bytes so callers never inherit locale-dependent decode errors.
    """
    kwargs.setdefault("text", True)
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("errors", "replace")
    return subprocess.run(*args, **kwargs)


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def _walk_files(root: Path) -> list[Path]:
    """Recursively collect all files under *root* using os.walk.

    Unlike ``Path.rglob``, this avoids the Windows MAX_PATH (260 char)
    limitation that causes ``Path.is_file()`` to silently return False
    for files with very long names.
    """
    collected: list[Path] = []
    for dirpath, _dirs, filenames in os.walk(root):
        for filename in filenames:
            collected.append(Path(dirpath) / filename)
    return collected


def get_files_in_folder(p: Path, suffix_accepted=None) -> list[Path]:
    """Return sorted list of files, optionally filtered by suffix."""
    files = _walk_files(p)
    if suffix_accepted:
        files = [f for f in files if f.suffix.lower() in suffix_accepted]
    return sorted(files, key=lambda f: f.stem)


def get_audio_files_in_folder(p: Path, suffix=None, print_non_audio=False) -> list[Path]:
    """Return sorted list of audio files under *p*."""
    from hometools.constants import AUDIO_SUFFIX

    suffix = suffix or AUDIO_SUFFIX
    all_files = _walk_files(p)
    audio_files = [f for f in all_files if f.suffix.lower() in suffix]
    audio_files = sorted(audio_files, key=lambda f: f.stem)
    if print_non_audio:
        non_audio = set(all_files) - set(audio_files)
        for x in non_audio:
            logger.info(f"Ignoring: {x}")
    return audio_files


# ---------------------------------------------------------------------------
# String / path helpers
# ---------------------------------------------------------------------------


def fix_spaces(s: str) -> str:
    """Collapse multiple spaces and strip leading/trailing spaces."""
    s = re.sub(r" {2,}", " ", s)
    return s.strip()


# Keep the old name as an alias so existing call-sites keep working during migration.
repath_fix_spaces = fix_spaces


def remove_ugly_spaces(s: str) -> str:
    """Alias for :func:`fix_spaces` (legacy name kept for compatibility)."""
    return fix_spaces(s)


# ---------------------------------------------------------------------------
# File size
# ---------------------------------------------------------------------------


def get_file_size(p: Path) -> int:
    """Return file size in bytes."""
    return os.stat(p).st_size


# ---------------------------------------------------------------------------
# Directory creation
# ---------------------------------------------------------------------------


def path_make_dir(p: Path) -> Path:
    """Ensure the directory (or parent dir of a file path) exists."""
    folder = p if not p.suffix else p.parent
    folder.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Renaming helpers
# ---------------------------------------------------------------------------


def rename_path(f: Path, new: Path):
    """Rename *f* to *new*, warning on collision."""
    try:
        f.rename(new)
    except FileExistsError:
        logger.warning(f"FileExistsError: {f} -> {new}  (skipped)")


def user_rename_file(f: Path, new: Path, ask_user_str=None):
    """Interactively ask the user before renaming."""
    prompt = ask_user_str or f'Renaming:\n\t{f}\n\t{new}\nEnter to continue. "n" to skip.'
    x = input(prompt)
    if x == "":
        rename_path(f, new)
    else:
        print("Skipped")


def user_rename_from_to_dict(from_to_dict: dict, confirm_each=True):
    """Rename files described by *from_to_dict* ``{old_path: new_path}``."""
    if not from_to_dict:
        print("No files to rename!")
        return

    if not confirm_each:
        for k, v in from_to_dict.items():
            print(f"{Colors.RED}{k}\n{Colors.GREEN}{v}{Colors.RESET}")
        x = input("Press Enter to rename all files above.")
        if x != "":
            print("Skipped!")
            return

    for k, v in from_to_dict.items():
        if confirm_each:
            user_rename_file(k, v)
        else:
            rename_path(k, v)


# Keep old name as alias
user_rename_fromToDict = user_rename_from_to_dict


# ---------------------------------------------------------------------------
# Soft-delete helpers
# ---------------------------------------------------------------------------


def attention_delete_files(paths, delete_dir: Path | None = None, soft_delete=True):
    """Move files to a trash directory (soft) or delete them (hard)."""
    delete_dir = delete_dir or get_delete_dir()
    path_make_dir(delete_dir)
    for p in paths:
        if soft_delete:
            dest = delete_dir / p.name
            logger.info(f"{p} -> {dest}")
            p.rename(dest)
        else:
            Path.unlink(p)


def deleting_file(p: Path, delete_dir: Path | None = None):
    """Interactively move a single file to the trash directory."""
    delete_dir = delete_dir or get_delete_dir()
    path_make_dir(delete_dir)
    dest = delete_dir / p.name
    user_rename_file(p, dest, ask_user_str=f"{p} -> {dest}")
