/**
 * Duplicate-detection formatting/key helpers — ported from
 * `player_js/_track_render.py`. Same "opportunistic port" rationale as
 * `pathUtils.ts` (see that file's header comment): all five functions are
 * pure and reference only each other, not any shared player state.
 *
 * `_dupeKey()`/`_normalizeStem()` build the `Map<key, [indices]>` used by
 * the client-side-only duplicate detection feature (docs/architecture.md
 * → "Duplicate detection"); `_fmtDuration`/`_fmtFileSize`/`_fmtDate` format
 * the dupe-panel's per-item metadata. Bridged onto `window` in main.ts —
 * legacy call sites in `player_js/_library_tools.py` (dupe panel rendering)
 * keep working unchanged via the scope-chain lookup.
 */

/** Minimal shape needed for duplicate-key computation — see
 * `legacy-globals.d.ts`'s `LegacyMediaItem` for the full contract. */
export interface DupeKeyItem {
  title?: string;
  artist?: string;
  relative_path?: string;
}

/** Format a duration in seconds as `m:ss` or `h:mm:ss` (dupe-panel display;
 * distinct from `fmtTime` in main.ts only in that it rounds first). */
export function _fmtDuration(secs: number | null | undefined): string {
  if (!secs) return "";
  const s = Math.round(secs);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return h + ":" + (m < 10 ? "0" : "") + m + ":" + (sec < 10 ? "0" : "") + sec;
  return m + ":" + (sec < 10 ? "0" : "") + sec;
}

/** Format a byte count for the dupe panel (GB/MB/KB/B, one decimal above KB). */
export function _fmtFileSize(bytes: number | null | undefined): string {
  if (!bytes) return "";
  if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + "\u00a0GB";
  if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + "\u00a0MB";
  if (bytes >= 1024) return Math.round(bytes / 1024) + "\u00a0KB";
  return bytes + "\u00a0B";
}

/** Format a unix timestamp (seconds) as a German `DD.MM.YYYY` date for the
 * dupe panel. */
export function _fmtDate(ts: number | null | undefined): string {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/** Strip promotional/platform noise (Official Video, prod./feat./vs.
 * separators, kbit-rate suffixes, domain suffixes, copy/kopie suffixes,
 * ...) from a title stem so different uploads of the same song normalize
 * to the same comparable string. Deliberately keeps version descriptors
 * (Remix, Extended, Live, Acoustic, ...) so different versions are NOT
 * flagged as duplicates — see `_dupeKey`'s doc comment. */
export function _normalizeStem(s: string | null | undefined): string {
  if (!s) return "";
  let out = s.replace(/&amp;/g, "&");
  out = out.replace(/\(\d{1,3}kbit_[A-Za-z]+\)/gi, "");
  out = out.replace(/\(Official[^)]*\)/gi, "");
  out = out.replace(/\((?:Audio|Video|Music\s+Video|Lyric\s+Video|Lyrics|Lyric|Visualizer|Topic|HD|HQ)\)/gi, "");
  out = out.replace(/\(\w*\.[a-zA-Z]{2,5}\)/gi, "");
  out = out.replace(/\w*\.(?:com|net|org|co\.uk|de|vu|ru|pl)/gi, "");
  out = out.replace(/(?<=\W)(?:featuring|feat\.|feat)\W/gi, "feat. ");
  out = out.replace(/(?<=\W)(?:produced by|produced|prod\. by|prod by|prod\.|prod)\W/gi, "prod. ");
  out = out.replace(/(?<=(?:\W|\(|\[))(?:vs\.|vs|versus)/gi, "vs. ");
  out = out.replace(/\(\s*\)|\[\s*\]/g, "");
  out = out.replace(/ {2,}/g, " ");
  return out.trim().toLowerCase();
}

/**
 * Build a stable dedupe key from artist + normalized title. Version/mix
 * descriptors are kept in the key on purpose so different versions of the
 * same song are NOT flagged as duplicates; artist is included so tracks
 * with the same title by different artists aren't either.
 */
export function _dupeKey(item: DupeKeyItem): string {
  let raw = item.title || "";
  if (!raw) {
    const rp = item.relative_path || "";
    const sl = rp.lastIndexOf("/");
    raw = sl >= 0 ? rp.substring(sl + 1) : rp;
    const dot = raw.lastIndexOf(".");
    if (dot > 0) raw = raw.substring(0, dot);
  }
  let cleaned = _normalizeStem(raw);
  cleaned = cleaned.replace(/[\s_-]*\(?(?:copy|kopie)\)?\s*$/i, "");
  cleaned = cleaned.replace(/[\s_-]+\d{1,2}\s*$/, "");
  cleaned = cleaned.replace(/\s*\(\d{1,2}\)\s*$/, "");
  cleaned = cleaned.replace(/\s*\[\d{1,2}\]\s*$/, "");
  let parts = cleaned.split(/feat\.|prod\.|vs\.|\(|\[| - |, | & |\)|\]/i);
  parts = parts.map((p) => p.replace(/\bofficial\b|\bexplicit\b|\bclean\b/gi, ""));
  parts = parts.map((p) => p.replace(/[^a-z0-9]/gi, ""));
  parts = parts.filter((p) => p.length > 2);
  const seen: Record<string, boolean> = {};
  const unique: string[] = [];
  parts.forEach((p) => {
    if (!seen[p]) {
      seen[p] = true;
      unique.push(p);
    }
  });
  unique.sort();
  let titleKey = unique.join("|");
  const artistRaw = (item.artist || "").toLowerCase().replace(/[^a-z0-9]/gi, "");
  if (artistRaw.length > 2) titleKey = artistRaw + "::" + titleKey;
  return titleKey;
}

/** Minimal shape needed for dupe-safety comparison. */
export interface DupeSafetyItem {
  file_size?: number;
  duration?: number;
}

const DUPE_SAFE_THRESHOLD = 0.02; // 2% max relative deviation in size/duration

/** True when every pair in a dupe group has file_size AND duration within
 * 2% of each other (missing values count as unsafe). */
export function _isDupeGroupSafe(groupItems: DupeSafetyItem[]): boolean {
  if (groupItems.length < 2) return true;
  for (let a = 0; a < groupItems.length; a++) {
    for (let b = a + 1; b < groupItems.length; b++) {
      const sA = groupItems[a].file_size || 0;
      const sB = groupItems[b].file_size || 0;
      const dA = groupItems[a].duration || 0;
      const dB = groupItems[b].duration || 0;
      if (!sA || !sB || Math.abs(sA - sB) / Math.max(sA, sB) > DUPE_SAFE_THRESHOLD) return false;
      if (!dA || !dB || Math.abs(dA - dB) / Math.max(dA, dB) > DUPE_SAFE_THRESHOLD) return false;
    }
  }
  return true;
}

