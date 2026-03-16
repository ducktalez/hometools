"""MP3 merging utilities using pydub."""

import logging
import re
from pathlib import Path

from pydub import AudioSegment
from pydub import utils as pydub_utils

logger = logging.getLogger(__name__)


def mp3merge_list(path_list: list[Path], p_merged: Path, meta_tag: dict | None = None):
    """Merge a list of audio files into a single MP3."""
    merged = sum(AudioSegment.from_file(p) for p in path_list)
    if meta_tag is None:
        meta_tag = pydub_utils.mediainfo(str(path_list[0]))
        meta_tag["TAG"]["track"] = str(len(path_list) + 1)
    merged.export(p_merged, format="mp3", bitrate="128k", tags=meta_tag)
    logger.info(f"Merged {len(path_list)} files → {p_merged}")


def merge_mp3files_in_folder(path_list: list[Path]):
    """Sort and merge MP3 files found in a folder by track number or filename digits."""
    mp3dict = {
        p: {
            "track": pydub_utils.mediainfo(str(p)).get("TAG", {}).get("track", "0"),
            "stem_digits": re.findall(r"\d+", p.stem),
        }
        for p in path_list
    }

    # Try sorting by track tag, then by last digit group, then by second digit group
    for key_func in [
        lambda x: int(x[1]["track"]),
        lambda x: int(x[1]["stem_digits"][-1]),
        lambda x: int(x[1]["stem_digits"][1]),
    ]:
        try:
            mp3sorted = [item[0] for item in sorted(mp3dict.items(), key=key_func)]
            break
        except (ValueError, IndexError):
            continue
    else:
        raise ValueError(f"Could not determine track order for: {path_list}")

    for p in mp3sorted:
        print(p.stem)

    return mp3sorted
