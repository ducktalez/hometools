/**
 * Smart playlist rule evaluator — ported from `player_js/_playlists.py`
 * (a client-side mirror of the server's `smart_playlists.py`, kept in sync
 * so a smart playlist re-evaluates instantly in the browser without a
 * round-trip whenever `allItems`/`_userPlaylists`/`_savedFavorites` change).
 *
 * Vite/TS migration — deliberate slice (not opportunistic), requested to
 * take priority over further header/toolbar work (see
 * docs/IMPLEMENTATION_PLAN.md → "Vite/TypeScript migration"). This is the
 * single largest *cohesive* piece of pure-ish logic left in `player_js/`:
 * every function here only touches its own parameters — the three legacy
 * globals it used to read directly (`allItems`, `_userPlaylists`,
 * `_savedFavorites`) are now explicit function arguments instead. That
 * sidesteps the `window`-bridge problem the Design Discussion
 * ("Player-JS-Modulkopplung") describes for *mutable, frequently
 * reassigned* globals: `originalTitle` (pathUtils.ts) is written once and
 * never touched again, so bridging it with a single `window.originalTitle
 * = originalTitle;` assignment works; `allItems`/`_userPlaylists`/
 * `_savedFavorites` are reassigned/mutated all over `player_js/*.py` —
 * keeping a `window` mirror in sync would need touching every one of
 * those call sites too. Passing them as parameters at the two remaining
 * legacy call sites (`_folder_browse.py`, `_playlists.py`'s own
 * `_resolvePlaylistItems`/`refreshSmartPlaylist`) is simpler and makes
 * this module verifiably pure — no `window` reads at all.
 */

/** One smart-playlist filter rule, as stored in the playlist JSON. */
export interface SmartPlaylistRule {
  field: string;
  op: string;
  value: unknown;
}

/** The `smart` block of a user playlist (absent/falsy = not a smart playlist). */
export interface SmartPlaylistSpec {
  match?: "all" | "any";
  rules: SmartPlaylistRule[];
  sort?: string;
  limit?: number;
}

/** Minimal shape of a user playlist as used by the evaluator (mirrors the
 * `PLAYLISTS_API_PATH` JSON — see `streaming/core/playlists.py`). */
export interface UserPlaylist {
  id: string;
  items?: string[];
  smart?: SmartPlaylistSpec;
}

/** `pl_id -> Set(relative_path)` index of every *non-smart* playlist's
 * membership — used to resolve `in_playlist` rules. Smart playlists are
 * skipped (no cascades, see "Smart-Playlist-Kaskaden" Design Discussion:
 * cycles are avoided by never resolving a smart playlist against another
 * smart playlist). */
export type SmartPlIndex = Record<string, Record<string, boolean>>;

const _smartRegexCache: Record<string, RegExp | null> = {};

/** Compile (and cache) a user-supplied regex pattern for the `matches` op.
 * Returns `null` for invalid patterns or ones exceeding the length guard
 * (256 chars) — callers must treat `null` as "never matches". */
export function smartCompile(pat: unknown): RegExp | null {
  if (typeof pat !== "string" || pat.length > 256) return null;
  if (pat in _smartRegexCache) return _smartRegexCache[pat];
  let rx: RegExp | null;
  try {
    rx = new RegExp(pat, "i");
  } catch {
    rx = null;
  }
  _smartRegexCache[pat] = rx;
  return rx;
}

/** Resolve a rule's `field` against an item, handling the three
 * synthetic/derived fields (`added_at`, `is_favorite`, `in_folder`) that
 * don't exist as-is on `MediaItem`. */
export function smartGetField(it: LegacyMediaItem, field: string, savedFavorites: Record<string, boolean>): unknown {
  if (field === "added_at") return Number(it.mtime || 0);
  if (field === "is_favorite") {
    return !!(savedFavorites && savedFavorites[it.relative_path]);
  }
  if (field === "in_folder") {
    const rp = String(it.relative_path || "");
    const i = rp.lastIndexOf("/");
    return i >= 0 ? rp.substring(0, i) : "";
  }
  return (it as Record<string, unknown>)[field];
}

/** Evaluate a single rule against one item. Never throws (mirrors the
 * server-side evaluator's "unknown input -> no match" fail-safe). */
export function smartEvalRule(rule: SmartPlaylistRule, it: LegacyMediaItem, plIndex: SmartPlIndex, savedFavorites: Record<string, boolean>): boolean {
  try {
    const field = String(rule.field || "");
    const op = String(rule.op || "");
    const value = rule.value;
    if (field === "in_playlist") {
      const rp = String(it.relative_path || "");
      const ids = Array.isArray(value) ? value : [value];
      const hits = ids.map((pid) => {
        const set = plIndex[String(pid)];
        return !!(set && set[rp]);
      });
      if (op === "any_of") return hits.some((h) => h);
      if (op === "all_of") return hits.length > 0 && hits.every((h) => h);
      if (op === "none_of") return !hits.some((h) => h);
      return false;
    }
    const actual = smartGetField(it, field, savedFavorites);
    if (field === "added_at") {
      const ts = Number(actual);
      const v = Number(value);
      if (!isFinite(ts) || !isFinite(v) || ts <= 0) return false;
      if (op === "within_days") return Date.now() / 1000 - ts <= v * 86400;
      if (op === "before") return ts < v;
      if (op === "after") return ts > v;
      return false;
    }
    let na: number, nv: number;
    switch (op) {
      case "eq":
        if (typeof actual === "string" && typeof value === "string") {
          return actual.toLowerCase() === value.toLowerCase();
        }
        return actual === value;
      case "contains":
        if (actual == null || value == null) return false;
        return String(actual).toLowerCase().indexOf(String(value).toLowerCase()) >= 0;
      case "starts_with":
        if (actual == null || value == null) return false;
        return String(actual).toLowerCase().indexOf(String(value).toLowerCase()) === 0;
      case "matches": {
        const rx = smartCompile(String(value || ""));
        return !!(rx && rx.test(String(actual == null ? "" : actual)));
      }
      case "gte":
        na = Number(actual);
        nv = Number(value);
        return isFinite(na) && isFinite(nv) && na >= nv;
      case "lte":
        na = Number(actual);
        nv = Number(value);
        return isFinite(na) && isFinite(nv) && na <= nv;
      case "between": {
        if (!Array.isArray(value) || value.length !== 2) return false;
        let lo = Number(value[0]);
        let hi = Number(value[1]);
        if (lo > hi) {
          const t = lo;
          lo = hi;
          hi = t;
        }
        na = Number(actual);
        return isFinite(na) && lo <= na && na <= hi;
      }
      case "in":
        if (!Array.isArray(value)) return false;
        return value.some((v) => {
          if (typeof actual === "string" && typeof v === "string") {
            return actual.toLowerCase() === v.toLowerCase();
          }
          return actual === v;
        });
      default:
        return false;
    }
  } catch {
    return false;
  }
}

/** Build the `in_playlist` resolution index from every *non-smart* user
 * playlist (smart playlists never cascade into other smart playlists). */
export function buildSmartPlIndex(userPlaylists: UserPlaylist[]): SmartPlIndex {
  const idx: SmartPlIndex = Object.create(null);
  (userPlaylists || []).forEach((pl) => {
    if (pl.smart && pl.smart.rules) return;
    const pid = String(pl.id || "");
    if (!pid) return;
    const set: Record<string, boolean> = Object.create(null);
    (pl.items || []).forEach((rp) => {
      set[String(rp)] = true;
    });
    idx[pid] = set;
  });
  return idx;
}

/** Sort a resolved item list per the smart playlist's `sort` key
 * (`<field>` ascending, `<field>_desc` descending, or `random`). Returns
 * the input unchanged (same array reference) for an unknown/empty key. */
export function smartApplySort(items: LegacyMediaItem[], sortKey: string | undefined): LegacyMediaItem[] {
  if (!sortKey) return items;
  const arr = items.slice();
  if (sortKey === "random") {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = arr[i];
      arr[i] = arr[j];
      arr[j] = tmp;
    }
    return arr;
  }
  const desc = sortKey.indexOf("_desc") === sortKey.length - 5 && sortKey.length > 5;
  const base = desc ? sortKey.substring(0, sortKey.length - 5) : sortKey;
  let keyFn: ((x: LegacyMediaItem) => string | number) | null = null;
  if (base === "title") keyFn = (x) => String(x.title || "").toLowerCase();
  if (base === "rating") keyFn = (x) => Number(x.rating || 0);
  if (base === "added_at") keyFn = (x) => Number(x.mtime || 0);
  if (base === "duration") keyFn = (x) => Number(x.duration || 0);
  if (!keyFn) return items;
  const fn = keyFn;
  arr.sort((a, b) => {
    const ka = fn(a);
    const kb = fn(b);
    if (ka < kb) return desc ? 1 : -1;
    if (ka > kb) return desc ? -1 : 1;
    return 0;
  });
  return arr;
}

/** Evaluate a smart playlist's rules against the full catalog. Returns
 * `[]` for a malformed/rule-less spec or on any unexpected error (never
 * throws — mirrors every other public function in this module). */
export function evaluateSmartPlaylist(
  pl: UserPlaylist | null | undefined,
  allItems: LegacyMediaItem[],
  userPlaylists: UserPlaylist[],
  savedFavorites: Record<string, boolean>
): LegacyMediaItem[] {
  try {
    const smart = pl && pl.smart;
    if (!smart || !Array.isArray(smart.rules) || smart.rules.length === 0) return [];
    const match = smart.match === "any" ? "any" : "all";
    const idx = buildSmartPlIndex(userPlaylists);
    const matched: LegacyMediaItem[] = [];
    (allItems || []).forEach((it) => {
      const results = smart.rules.map((r) => smartEvalRule(r, it, idx, savedFavorites));
      const keep = match === "all" ? results.every((v) => v) : results.some((v) => v);
      if (keep) matched.push(it);
    });
    let out = smart.sort ? smartApplySort(matched, String(smart.sort)) : matched;
    if (typeof smart.limit === "number" && smart.limit > 0) {
      out = out.slice(0, smart.limit);
    }
    return out;
  } catch {
    return [];
  }
}

