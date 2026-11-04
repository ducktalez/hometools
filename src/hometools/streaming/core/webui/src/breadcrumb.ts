/**
 * Folder-name cleanup + breadcrumb markup — ported from `player_js/_queue.py`.
 *
 * Vite/TS migration Phase 5 opportunistic-port slice
 * (docs/IMPLEMENTATION_PLAN.md → "Vite/TypeScript migration" /
 * "UI-Template-Vereinheitlichung"). `cleanFolderName` and the breadcrumb
 * segment/markup builders are pure (string/array in, string out) — no
 * dependency on the shared player state described in `legacy-globals.d.ts`.
 *
 * `renderBreadcrumb(hooks)` is the DOM-wiring half (visibility toggling,
 * click handlers); `currentPath` via `htState`, DOM refs/`showFolderView`
 * via hooks.
 *
 * `cleanFolderName` was previously declared as a legacy-owned function in
 * `legacy-globals.d.ts` (typed for future consumers) — now that it's a
 * real ported implementation, that ambient entry was removed there.
 */

import { getState } from "./stateBridge";

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

export interface BreadcrumbEl {
  classList: { add(c: string): void; remove(c: string): void };
  innerHTML: string;
  querySelectorAll(sel: string): ArrayLike<{ dataset: { path?: string }; addEventListener(t: string, f: () => void): void }>;
}

export interface BreadcrumbHooks {
  breadcrumb: BreadcrumbEl;
  headerTitle: { style: { display: string } };
  escHtml: (s: unknown) => string;
  showFolderView(): void;
}

/** Render the header breadcrumb for htState.currentPath; link clicks navigate. */
export function renderBreadcrumb(h: BreadcrumbHooks): void {
  const s = getState();
  if (!s) return;
  if (!s.currentPath) {
    h.breadcrumb.classList.remove("visible");
    h.headerTitle.style.display = "";
    return;
  }
  h.breadcrumb.classList.add("visible");
  h.headerTitle.style.display = "none";
  h.breadcrumb.innerHTML = renderBreadcrumbHtml(s.currentPath, h.escHtml);
  const links = h.breadcrumb.querySelectorAll("a");
  for (let i = 0; i < links.length; i++) {
    const a = links[i];
    a.addEventListener("click", () => {
      s.currentPath = a.dataset.path || "";
      h.showFolderView();
    });
  }
}

