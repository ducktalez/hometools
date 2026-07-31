/**
 * Path/filename helpers — ported from `player_js/_search_filter.py`.
 *
 * Chosen as a Vite/TS migration Phase 5 "opportunistic port" slice
 * (docs/IMPLEMENTATION_PLAN.md → "Vite/TypeScript migration"): both
 * functions are pure (string in, string/boolean out), reference only the
 * `NATIVE_EXT` constant defined in the same original fragment (moved here
 * alongside them), and have zero dependency on the shared player state
 * described in `legacy-globals.d.ts` — the precondition that made
 * `fmtTime`/`escHtml`/`formatBytes` (main.ts) and the dupe-detection
 * helpers (dupeUtils.ts) safe to port before the bigger, stateful
 * fragments (`_core.py`, `_library_tools.py`, ...).
 *
 * `filenameFromPath` was originally declared in `_search_filter.py` but
 * called from `_track_render.py` — a concrete example of the cross-
 * fragment coupling the Design Discussion describes; it "just worked"
 * because both fragments concatenate into one shared script scope. Now
 * that it's bridged onto `window` (see main.ts), every legacy call site
 * (bare `filenameFromPath(...)`) keeps resolving unchanged through the
 * normal JS scope chain — no call-site edits needed.
 *
 * `parentPath`/`leafName` (originally in `player_js/_queue.py`, part of
 * the "UI-Template-Vereinheitlichung" header work — see
 * docs/IMPLEMENTATION_PLAN.md) were added in the same opportunistic-port
 * pass: `parentPath` is fully pure; `leafName` reads `window.originalTitle`
 * `leafName` (a read-only global set once in `_core.py`, now declared in
 * `legacy-globals.d.ts`) and calls the already-ported `cleanFolderName`
 * (breadcrumb.ts) — both preconditions the Opportunistic migration rule
 * requires before a stateful-adjacent function qualifies.
 *
 * `currentFolderOf` (originally `_currentFolderOf` in `_library_tools.py`,
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

