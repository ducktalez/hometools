"""Video library organizer using TMDB for metadata.

Renames movie and series files to match TMDB naming conventions,
which is compatible with media servers like Jellyfin and Plex.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tmdbv3api import Movie, Season, TMDb, TV

from hometools.config import get_tmdb_api_key
from hometools.constants import VIDEO_SUFFIX
from hometools.utils import (
    attention_delete_files,
    get_files_in_folder,
    fix_spaces,
    user_rename_from_to_dict,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def split_for_search(s: str) -> list[str]:
    """Split a title string for fuzzy TMDB searching."""
    s = re.sub(r'\(engl\)', '', s)
    s = re.sub(r'(\d){1,4}p', '', s, flags=re.IGNORECASE)
    s = re.sub(r'uncut|extended|edition', '', s, flags=re.IGNORECASE)
    s = re.sub(r'x264|BluRay|DD51', '', s, flags=re.IGNORECASE)
    s = re.sub(r'tmdbid', '', s, flags=re.IGNORECASE)
    splits = re.split(r'\W', s)
    splits = [fix_spaces(x) for x in splits]
    splits = [
        x for i, x in enumerate(splits)
        if (i < 2 or len(x) > 2 or re.findall(r'\d{1,3}', x))
    ]
    return splits


def re_umlaute_replace(s: str, reverse: bool = False) -> str:
    """Replace German umlauts with their ASCII equivalents (or reverse)."""
    umlaute = {'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss'}
    for k, v in umlaute.items():
        if reverse:
            k, v = v, k
        s = re.sub(k, v, s)
        s = re.sub(k.upper(), v.upper(), s)
    return s


def sanitize_path(path: str, replacement: str = "_") -> str:
    """Replace characters that are invalid in file paths."""
    invalid = r'[<>:"/\\|?*\x00-\x1F]'
    windows_reserved = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    sanitized = re.sub(invalid, replacement, path)
    parts = sanitized.split("/")
    parts = [f"{p}{replacement}" if p.upper() in windows_reserved else p for p in parts]
    sanitized = "/".join(parts)
    return re.sub(r"[. ]+$", replacement, sanitized)


# ---------------------------------------------------------------------------
# TMDB movie helpers
# ---------------------------------------------------------------------------


def get_tmdb_from_name(search_str: str, movie: Movie) -> list[dict]:
    """Search TMDB for *search_str* and return ranked results."""
    tmdb_search = movie.search(search_str)
    if tmdb_search.total_results == 0:
        raise ValueError(f'No TMDB results for "{search_str}"')

    results = []
    for result in tmdb_search:
        title_split = split_for_search(result.title)
        try:
            release_year = int(result['release_date'][:4])
        except (ValueError, TypeError):
            continue
        og_split = split_for_search(result.original_title)
        og_perc = sum(len(x) for x in og_split if x in search_str) / max(len(''.join(og_split)), 1)
        title_perc = sum(len(x) for x in title_split if x in search_str) / max(len(''.join(title_split)), 1)

        results.append({
            'result.title': result.title,
            'original_title': result.original_title,
            'max_perc': max(title_perc, og_perc),
            'og_perc': og_perc,
            'title_perc': title_perc,
            'release_match': str(release_year) in search_str,
            'release_year': release_year,
            'result': result,
        })

    results.sort(key=lambda x: (-x['max_perc'], -x['og_perc'], -x['title_perc'], -x['result']['vote_count']))
    for x in results:
        logger.info(
            f'TMDB: "{x["result.title"]}" {x["max_perc"]:.0%} match '
            f'(og={x["og_perc"]:.0%}, title={x["title_perc"]:.0%}, '
            f'original={x["original_title"]})'
        )
    return results


def film_title_add_counter(search_split: list[str], title: str) -> str:
    """Optionally inject a numeric counter into the title (e.g. Harry Potter 1)."""
    if not search_split[-1] in title and re.findall(r'\d', search_split[-1]):
        try_find = ' '.join(search_split[:-1])
        try_replace = ' '.join(search_split)
        enhanced = re.sub(try_find, try_replace, title)
        if enhanced != title:
            return enhanced
    return title


def get_leftovers(p: Path, tmdb_result: dict) -> str:
    """Extract filename parts not covered by TMDB metadata (e.g. codec tags)."""
    tmdb_id = tmdb_result['result']['id']
    title = tmdb_result['result']['title']
    original_title = tmdb_result['result']['original_title']
    release_year = tmdb_result['release_year']

    db_set = set(
        re.sub(r'\W', '', e).lower()
        for e in (
            title.split() + original_title.split()
            + [f'[tmdbid-{tmdb_id}]', f'({release_year})']
        )
    )
    file_parts = [re.sub(r'\W', '', e).lower() for e in re.split(r'\W', p.stem) if e]
    left = set(file_parts) - db_set
    left_final = [x for x in file_parts if any(re.search(x, l, re.IGNORECASE) for l in left)]
    if left_final:
        return ' [' + ' '.join(x for x in left_final if len(x) > 1) + ']'
    return ''


def get_tmdbid_from_path(p: Path, movie: Movie) -> dict:
    """Determine the best TMDB match for a file and return the rename mapping."""
    search_split = split_for_search(p.stem)

    while search_split:
        search_str = ' '.join(search_split)
        try:
            results = get_tmdb_from_name(search_str, movie)
            best = results[0]
            tmdb_id = best['result']['id']
            title = best['result']['title']
            year = best['release_year']
            leftovers = get_leftovers(p, best)
            title_v2 = film_title_add_counter(search_split, title)
            rename_as = f'{title_v2} ({year}){leftovers} [tmdbid-{tmdb_id}]{p.suffix}'
            return {p: {'rename_as': rename_as}}
        except (ValueError, TypeError):
            search_split.pop()

    raise ValueError(f'No TMDB matches found for {p}')


# ---------------------------------------------------------------------------
# TMDB series helpers
# ---------------------------------------------------------------------------


def tmdb_serie_infos(serie_id: int, season_api: Season, tv: TV) -> dict:
    """Fetch all episode data for a series."""
    tv_show = tv.details(serie_id)
    season_dict = {n: season_api.details(tv_show.id, n) for n in range(tv_show.number_of_seasons + 1)}
    return {
        n: {e.episode_number: {'tmdb': e} for e in details.episodes}
        for n, details in season_dict.items()
    }


def serie_path_to_numbers(p: Path) -> dict:
    """Extract season and episode numbers from a filename."""
    match = re.search(r"S(\d{1,2})E(\d{1,4})", p.stem, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"No S##E## pattern found in: {p.stem}")
    return {'season': int(match.group(1)), 'episode': int(match.group(2))}


def delete_jellyfin_meta_files(p: Path):
    """Delete metadata files created by Jellyfin (.nfo, .jpg, .png, .svg)."""
    suffixes = ['.nfo', '.jpg', '.png', '.svg']
    files = get_files_in_folder(p, suffix_accepted=suffixes)
    for f in files:
        logger.info(f'Delete: {f}')
    attention_delete_files(files, soft_delete=False)

    for d in sorted(p.glob('**/*/'), reverse=True):
        try:
            d.rmdir()
            logger.info(f'Deleted empty dir: {d}')
        except OSError:
            pass


def series_rename_episodes(
    dir_p: Path,
    season_api: Season,
    tv: TV,
    ignore_substrings: list[str] | None = None,
):
    """Rename series episodes in *dir_p* based on TMDB metadata."""
    series_name = re.sub(r'#|\(engl\)', '', dir_p.name, flags=re.IGNORECASE)
    if ignore_substrings:
        for ss in ignore_substrings:
            series_name = re.sub(ss, '', series_name)

    tmdb_search = tv.search(series_name)
    try:
        e_dict = tmdb_serie_infos(tmdb_search['results'][0].id, season_api, tv)
    except TypeError:
        logger.warning(f'Skipping (no TMDB data): {series_name}')
        return

    from_to: dict[Path, Path] = {}

    for p in get_files_in_folder(dir_p, suffix_accepted=VIDEO_SUFFIX):
        try:
            se = serie_path_to_numbers(p)
        except ValueError:
            logger.warning(f'Could not parse S##E## from {p}')
            continue

        s, e = se['season'], se['episode']
        p_stem = re.sub(r'[._]', ' ', p.stem)
        p_stem = re.sub(r'\(\)', ' ', p_stem)
        p_stem = re.sub(r'\(engl\)', '', p_stem)
        p_stem = re.sub(series_name, '', p_stem, flags=re.IGNORECASE)
        p_stem = re.sub(r'S\d{1,2}E\d{1,4}', '', p_stem, flags=re.IGNORECASE)

        db_name = e_dict[s][e]['tmdb'].name
        remove_words = set(re.split(r'\W', db_name) + re.split(r'\W', re_umlaute_replace(db_name)))
        remove_words = sorted(remove_words, key=len, reverse=True)
        for w in (x for x in remove_words if len(x) > 1):
            p_stem = re.sub(w, '', p_stem, flags=re.IGNORECASE)
        p_stem = re.sub(r'\b\w{1,1}\b', '', p_stem)
        p_stem = re.sub(db_name, '', p_stem, flags=re.IGNORECASE)

        leftovers = [x for x in re.split(r'\W', p_stem) if x]
        leftovers_str = f' [{" ".join(leftovers)}]' if leftovers else ''

        new_name = fix_spaces(f'{series_name} S{s:02d}E{e:02d} {db_name}{leftovers_str}{p.suffix}')
        new_name = sanitize_path(new_name, replacement='_')
        new_path = p.parent / new_name

        if p != new_path:
            from_to[p] = new_path

    user_rename_from_to_dict(from_to, confirm_each=False)


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------


def run_series_renaming(series_root: Path, language: str = "de"):
    """Rename all series under *series_root* using TMDB."""
    from tmdbv3api import Movie, Season, TMDb, TV

    tmdb = TMDb()
    tmdb.api_key = get_tmdb_api_key()
    tmdb.language = language

    movie = Movie()
    tv = TV()
    season_api = Season()

    for dir_p in series_root.glob('**/*/'):
        if any(x in str(dir_p) for x in ['#recycle', '#REST']):
            continue
        if not dir_p.is_dir():
            continue
        try:
            series_rename_episodes(
                dir_p, season_api, tv,
                ignore_substrings=[r'\(engl, gersub\)', r'\(engl\)', '1-8', '9-Rest'],
            )
        except Exception as ex:
            logger.error(f'Error renaming {dir_p}: {ex}')
