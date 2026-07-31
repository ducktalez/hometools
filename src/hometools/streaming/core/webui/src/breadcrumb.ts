/**
 * Folder-name cleanup + breadcrumb markup — ported from `player_js/_queue.py`.
 *
 * Vite/TS migration Phase 5 opportunistic-port slice
 * (docs/IMPLEMENTATION_PLAN.md → "Vite/TypeScript migration" /
 * "UI-Template-Vereinheitlichung"). `cleanFolderName` and the breadcrumb
 * segment/markup builders are pure (string/array in, string out) — no
 * dependency on the shared player state described in `legacy-globals.d.ts`.
 *
 * The DOM-wiring half of the old `renderBreadcrumb()` (toggling
 * `.breadcrumb`/`.logo-title` visibility, attaching click handlers that
 * call `showFolderView()`) stays in `player_js/_queue.py` — that part
 * *is* stateful/cross-fragment-coupled (reads `currentPath`, writes
 * `breadcrumb`/`headerTitle` DOM refs, calls a function owned by
 * `_folder_browse.py`), same split as `renderBpmPill` (pure, ported) vs.
 * `_openBpmAdjustMenu` (stateful, stays Python) in `metricPill.ts`.
 *
 * `cleanFolderName` was previously declared as a legacy-owned function in
 * `legacy-globals.d.ts` (typed for future consumers) — now that it's a
 * real ported implementation, that ambient entry was removed there.
 */

/** Strips the `#` favourite-prefix and any `(lang[, subLang])` tag suffix
 * from a raw folder name, e.g. `"#Show (engl, gersub)"` → `"Show"`. */
const LANG_TAG_RE =
  /\s*\(\s*(?:engl(?:ish)?|eng|en|german|deutsch|ger|de|french|fran[cç]ais(?:e)?|fr|spanish|espa[nñ]ol|es|italian(?:o)?|it|japanese|jap|jpn?|ja|korean|kor?|ko|chinese|zh|portuguese|pt|russian|ru)(?:\s*,\s*(?:ger|de|eng|en)(?:\s*sub(?:s)?)?)?\s*\)/gi;

export function cleanFolderName(name: string): string {
  let n = name;
  if (n.charAt(0) === "#") n = n.substring(1);
  n = n.replace(LANG_TAG_RE, "");
  return n.replace(/\s{2,}/g, " ").trim();
}

export interface BreadcrumbSegment {
  path: string;
  label: string;
  isCurrent: boolean;
}

/** Pure breadcrumb segment list for a `currentPath` (`""` → no segments,
 * i.e. hidden). `"__offline__"` is the special pseudo-path for the
 * Downloaded/offline-library view — a single, non-navigable segment. */
export function breadcrumbSegments(currentPath: string): BreadcrumbSegment[] {
  if (!currentPath) return [];
  if (currentPath === "__offline__") {
    return [{ path: "__offline__", label: "Downloaded", isCurrent: true }];
  }
  const parts = currentPath.split("/");
  return parts.map((part, i) => ({
    path: parts.slice(0, i + 1).join("/"),
    label: cleanFolderName(part),
    isCurrent: i === parts.length - 1,
  }));
}

/** Builds the breadcrumb's inner HTML (separators + links/current label).
 * No leading "Home" entry — the header's Home button already covers that
 * navigation, so repeating it here would be redundant (see
 * docs/architecture.md → header section). */
export function renderBreadcrumbHtml(currentPath: string, escHtmlFn: (s: unknown) => string): string {
  return breadcrumbSegments(currentPath)
    .map((seg) => {
      const sep = '<span class="sep">\u203A</span>';
      if (seg.isCurrent) {
        return sep + '<span class="current">' + escHtmlFn(seg.label) + "</span>";
      }
      return sep + '<a data-path="' + escHtmlFn(seg.path) + '">' + escHtmlFn(seg.label) + "</a>";
    })
    .join("");
}

