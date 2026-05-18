"""Smart playlist rule evaluation.

A *smart playlist* stores a set of filter rules instead of a fixed list of
items.  At resolution time the rules are evaluated against the current
library (`allItems`) and the available user playlists (for cross-playlist
references) to produce a concrete list of `relative_path` strings.

Storage shape (lives on the playlist dict under the ``smart`` key)::

    {
      "match": "all" | "any",         # AND vs OR across top-level rules
      "rules": [
        {"field": "rating",      "op": "gte",          "value": 4},
        {"field": "in_playlist", "op": "any_of",       "value": [pl_id, ...]},
        {"field": "added_at",    "op": "within_days",  "value": 60},
        {"field": "genre",       "op": "matches",      "value": "^Rock"},
        ...
      ],
      "limit": 100,                    # optional, applied after sort
      "sort": "rating_desc"            # optional: title|title_desc|rating|
                                       # rating_desc|added_at|added_at_desc|
                                       # duration|duration_desc|random
    }

Design rules (per the project instructions):

* **Exception-safe.** Every public function returns sensible defaults
  (``[]`` or input) on failure and never raises.
* **No side effects.** Pure evaluation.
* **Regex safety.** Patterns are compiled once and cached; invalid
  patterns silently never match.
* **Phase 1 limitations** (documented in ``docs/IMPLEMENTATION_PLAN.md``):
  - No nested groups; top-level ``match`` only.
  - ``in_playlist`` may only reference *non-smart* playlists.  Smart
    playlists referencing other smart playlists are skipped (cascade
    cycles are an explicit Design Discussion topic).
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterable
from typing import Any

logger = logging.getLogger(__name__)

_DAY_SECONDS = 86_400.0

# Regex compile cache (pattern_str -> compiled or None for invalid).
_regex_cache: dict[str, re.Pattern[str] | None] = {}


def _compile(pattern: str) -> re.Pattern[str] | None:
    """Compile a regex pattern with caching; return ``None`` on failure."""
    if not isinstance(pattern, str) or len(pattern) > 256:
        return None
    if pattern in _regex_cache:
        return _regex_cache[pattern]
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error:
        compiled = None
    _regex_cache[pattern] = compiled
    return compiled


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------


_STR_FIELDS = {"title", "artist", "genre", "relative_path", "language", "subtitle_language"}
_NUM_FIELDS = {"rating", "duration", "season", "episode", "bitrate", "file_size"}


def _get_field(item: dict[str, Any], field: str) -> Any:
    """Read *field* from an item dict (MediaItem.to_dict() shape)."""
    if field == "added_at":
        return float(item.get("mtime") or 0.0)
    if field == "is_favorite":
        # Not part of MediaItem; resolved by caller via context.
        return None
    if field == "in_folder":
        rp = str(item.get("relative_path") or "")
        return rp.rsplit("/", 1)[0] if "/" in rp else ""
    return item.get(field)


# ---------------------------------------------------------------------------
# Operator implementations
# ---------------------------------------------------------------------------


def _op_eq(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str) and isinstance(expected, str):
        return actual.casefold() == expected.casefold()
    return actual == expected


def _op_contains(actual: Any, needle: Any) -> bool:
    if actual is None or needle is None:
        return False
    return str(needle).casefold() in str(actual).casefold()


def _op_starts_with(actual: Any, prefix: Any) -> bool:
    if actual is None or prefix is None:
        return False
    return str(actual).casefold().startswith(str(prefix).casefold())


def _op_matches(actual: Any, pattern: Any) -> bool:
    if actual is None or not isinstance(pattern, str):
        return False
    compiled = _compile(pattern)
    if compiled is None:
        return False
    try:
        return compiled.search(str(actual)) is not None
    except Exception:
        return False


def _to_number(value: Any) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _op_gte(actual: Any, threshold: Any) -> bool:
    a, b = _to_number(actual), _to_number(threshold)
    if a is None or b is None:
        return False
    return a >= b


def _op_lte(actual: Any, threshold: Any) -> bool:
    a, b = _to_number(actual), _to_number(threshold)
    if a is None or b is None:
        return False
    return a <= b


def _op_between(actual: Any, bounds: Any) -> bool:
    if not isinstance(bounds, list | tuple) or len(bounds) != 2:
        return False
    lo, hi = _to_number(bounds[0]), _to_number(bounds[1])
    a = _to_number(actual)
    if a is None or lo is None or hi is None:
        return False
    if lo > hi:
        lo, hi = hi, lo
    return lo <= a <= hi


def _op_in(actual: Any, values: Any) -> bool:
    if not isinstance(values, list | tuple):
        return False
    return any(_op_eq(actual, v) for v in values)


def _op_within_days(actual_ts: Any, days: Any, *, now: float | None = None) -> bool:
    ts = _to_number(actual_ts)
    d = _to_number(days)
    if ts is None or d is None or ts <= 0 or d <= 0:
        return False
    current = now if now is not None else time.time()
    return (current - ts) <= d * _DAY_SECONDS


def _op_before(actual_ts: Any, cutoff_ts: Any) -> bool:
    ts = _to_number(actual_ts)
    cutoff = _to_number(cutoff_ts)
    if ts is None or cutoff is None:
        return False
    return ts < cutoff


def _op_after(actual_ts: Any, cutoff_ts: Any) -> bool:
    ts = _to_number(actual_ts)
    cutoff = _to_number(cutoff_ts)
    if ts is None or cutoff is None:
        return False
    return ts > cutoff


# ---------------------------------------------------------------------------
# Rule evaluation
# ---------------------------------------------------------------------------


def _evaluate_rule(
    rule: dict[str, Any],
    item: dict[str, Any],
    *,
    playlist_index: dict[str, set[str]],
    favorites: set[str],
    now: float | None = None,
) -> bool:
    """Evaluate a single rule against *item*.  Returns ``False`` on any error."""
    try:
        field = str(rule.get("field") or "")
        op = str(rule.get("op") or "")
        value = rule.get("value")

        # --- Playlist-membership rules (special: read from playlist_index)
        if field == "in_playlist":
            rp = str(item.get("relative_path") or "")
            if not isinstance(value, list | tuple):
                value = [value]
            pl_ids = [str(v) for v in value if v]
            memberships = [rp in playlist_index.get(pid, set()) for pid in pl_ids]
            if op == "any_of":
                return any(memberships)
            if op == "all_of":
                return bool(memberships) and all(memberships)
            if op == "none_of":
                return not any(memberships)
            return False

        # --- Favorites
        if field == "is_favorite":
            rp = str(item.get("relative_path") or "")
            is_fav = rp in favorites
            want = bool(value)
            if op in ("", "eq"):
                return is_fav == want
            return False

        # --- Regular field-based rules
        actual = _get_field(item, field)

        if field == "added_at" and op == "within_days":
            return _op_within_days(actual, value, now=now)
        if field == "added_at" and op == "before":
            return _op_before(actual, value)
        if field == "added_at" and op == "after":
            return _op_after(actual, value)

        if op == "eq":
            return _op_eq(actual, value)
        if op == "contains":
            return _op_contains(actual, value)
        if op == "starts_with":
            return _op_starts_with(actual, value)
        if op == "matches":
            return _op_matches(actual, value)
        if op == "gte":
            return _op_gte(actual, value)
        if op == "lte":
            return _op_lte(actual, value)
        if op == "between":
            return _op_between(actual, value)
        if op == "in":
            return _op_in(actual, value)

        return False
    except Exception:
        logger.debug("Rule evaluation failed for %r", rule, exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Sort + limit helpers
# ---------------------------------------------------------------------------


def _apply_sort(items: list[dict[str, Any]], sort_key: str) -> list[dict[str, Any]]:
    """Return a new sorted list according to *sort_key*."""
    if not sort_key:
        return items
    try:
        if sort_key == "random":
            import random

            shuffled = items[:]
            random.shuffle(shuffled)
            return shuffled
        reverse = sort_key.endswith("_desc")
        base = sort_key[:-5] if reverse else sort_key
        if base == "title":
            return sorted(items, key=lambda x: str(x.get("title") or "").casefold(), reverse=reverse)
        if base == "rating":
            return sorted(items, key=lambda x: float(x.get("rating") or 0.0), reverse=reverse)
        if base == "added_at":
            return sorted(items, key=lambda x: float(x.get("mtime") or 0.0), reverse=reverse)
        if base == "duration":
            return sorted(items, key=lambda x: float(x.get("duration") or 0.0), reverse=reverse)
        return items
    except Exception:
        return items


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_smart(playlist: dict[str, Any] | None) -> bool:
    """Return ``True`` if *playlist* has a ``smart`` rule block."""
    if not isinstance(playlist, dict):
        return False
    smart = playlist.get("smart")
    return isinstance(smart, dict) and isinstance(smart.get("rules"), list)


def evaluate_smart(
    smart: dict[str, Any],
    all_items: Iterable[dict[str, Any]],
    *,
    all_playlists: list[dict[str, Any]] | None = None,
    favorites: Iterable[str] | None = None,
    now: float | None = None,
) -> list[str]:
    """Evaluate *smart* rules against *all_items*.

    Returns a list of ``relative_path`` strings, optionally sorted and
    capped to ``smart["limit"]``.  Never raises; returns ``[]`` on any
    error or empty input.
    """
    try:
        if not isinstance(smart, dict):
            return []
        rules = smart.get("rules") or []
        if not isinstance(rules, list) or not rules:
            return []
        match = str(smart.get("match") or "all").lower()
        if match not in ("all", "any"):
            match = "all"

        # Build playlist_index: pl_id -> set of relative_paths (non-smart only).
        playlist_index: dict[str, set[str]] = {}
        for pl in all_playlists or []:
            if not isinstance(pl, dict):
                continue
            if is_smart(pl):
                # Phase 1: skip smart playlists when resolving in_playlist —
                # avoids cascade cycles.  See implementation plan Design
                # Discussion for the planned Phase 2 DAG handling.
                continue
            pid = str(pl.get("id") or "")
            if not pid:
                continue
            items = pl.get("items") or []
            if isinstance(items, list):
                playlist_index[pid] = {str(rp) for rp in items if rp}

        fav_set: set[str] = set(favorites) if favorites else set()
        items_list = [it for it in all_items if isinstance(it, dict)]

        matched: list[dict[str, Any]] = []
        for item in items_list:
            results = [
                _evaluate_rule(
                    r,
                    item,
                    playlist_index=playlist_index,
                    favorites=fav_set,
                    now=now,
                )
                for r in rules
                if isinstance(r, dict)
            ]
            if not results:
                continue
            keep = all(results) if match == "all" else any(results)
            if keep:
                matched.append(item)

        sort_key = str(smart.get("sort") or "")
        if sort_key:
            matched = _apply_sort(matched, sort_key)

        limit = smart.get("limit")
        if isinstance(limit, int | float) and limit > 0:
            matched = matched[: int(limit)]

        return [str(it.get("relative_path") or "") for it in matched if it.get("relative_path")]
    except Exception:
        logger.debug("evaluate_smart failed", exc_info=True)
        return []


def validate_smart_rules(smart: Any) -> tuple[bool, str]:
    """Lightweight validator for a ``smart`` rule block.

    Returns ``(ok, reason)``.  Used by API endpoints to reject obviously
    malformed payloads before persisting them.
    """
    if not isinstance(smart, dict):
        return False, "smart must be an object"
    rules = smart.get("rules")
    if not isinstance(rules, list) or not rules:
        return False, "smart.rules must be a non-empty list"
    if len(rules) > 32:
        return False, "smart.rules exceeds 32 entries"
    match = smart.get("match", "all")
    if match not in ("all", "any"):
        return False, "smart.match must be 'all' or 'any'"
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            return False, f"rule[{idx}] must be an object"
        if not rule.get("field") or not isinstance(rule.get("field"), str):
            return False, f"rule[{idx}].field is required"
        if not rule.get("op") or not isinstance(rule.get("op"), str):
            return False, f"rule[{idx}].op is required"
        if "value" not in rule:
            return False, f"rule[{idx}].value is required"
    limit = smart.get("limit")
    if limit is not None and (not isinstance(limit, int | float) or limit < 0 or limit > 10_000):
        return False, "smart.limit must be 0–10000"
    return True, ""


__all__ = [
    "evaluate_smart",
    "is_smart",
    "validate_smart_rules",
]
