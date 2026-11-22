/**
 * Path/filename helpers
 *
 * Chosen as a Vite/TS migration Phase 5 "opportunistic port" slice
 * (docs/IMPLEMENTATION_PLAN.md → "Vite/TypeScript migration"): both
 * functions are pure (string in, string/boolean out), reference only the
 * alongside them), and have zero dependency on the shared player state
 * described in `globals.d.ts` — the precondition that made
 * `fmtTime`/`escHtml`/`formatBytes` (main.ts) and the dupe-detection
 * helpers (dupeUtils.ts) safe to port before the bigger, stateful
 *
 * (bare `filenameFromPath(...)`) keeps resolving unchanged through the
 * normal JS scope chain — no call-site edits needed.
 *
 * the "UI-Template-Vereinheitlichung" header work — see
 * docs/IMPLEMENTATION_PLAN.md) were added in the same opportunistic-port
 * pass: `parentPath` is fully pure; `leafName` reads `window.originalTitle`
 * (breadcrumb.ts) — both preconditions the Opportunistic migration rule
 * requires before a stateful-adjacent function qualifies.
 *
 * file-mover widget) is pure and added in the same pass.
 */

import { cleanFolderName } from "./breadcrumb";

/** File extensions the `<audio>`/`<video>` element can play natively —
 * anything else gets on-the-fly server-side remuxing/transcoding (see
 * `streaming/core/remux.py`). */
export const NATIVE_EXT = [
  ".mp4", ".m4v", ".webm", ".ogg", ".ogv", ".mp3", ".m4a", ".aac", ".opus", ".flac", ".wav",
];

/** True when the relative path's extension needs server-side conversion
 * before it can play in the browser natively. */
export function needsConversion(rp: string | null | undefined): boolean {
  if (!rp) return false;
  const dot = rp.lastIndexOf(".");
  if (dot < 0) return false;
  return NATIVE_EXT.indexOf(rp.substring(dot).toLowerCase()) < 0;
}

/** Extract the filename (without extension) from a relative path. */
export function filenameFromPath(rp: string | null | undefined): string {
  if (!rp) return "";
  const slash = rp.lastIndexOf("/");
  const name = slash >= 0 ? rp.substring(slash + 1) : rp;
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.substring(0, dot) : name;
}

/** Parent directory of a `/`-joined relative path (`""` for a top-level
 * path or the root itself). */
export function parentPath(path: string): string {
  if (!path) return "";
  const i = path.lastIndexOf("/");
  return i >= 0 ? path.substring(0, i) : "";
}

/** Display label for the last segment of `path`, falling back to the
 * page's original header title (`window.originalTitle`) at the root. */
export function leafName(path: string): string {
  if (!path) return window.originalTitle;
  const i = path.lastIndexOf("/");
  const raw = i >= 0 ? path.substring(i + 1) : path;
  return cleanFolderName(raw);
}

/** Top-level folder of a relative path (first `/` segment), or `""` for a
 * root-level item — used by the file-mover widget's "current folder"
 * display. Distinct from `parentPath` (last segment). */
export function currentFolderOf(item: { relative_path?: string }): string {
  const rp = item.relative_path || "";
  const sl = rp.indexOf("/");
  return sl > 0 ? rp.substring(0, sl) : "";
}

