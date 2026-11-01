/**
 * Folder-browse UI helpers — ported from `player_js/_folder_browse.py`:
 * language picker, filter-bar scroll reveal, global-search wiring and the
 * playlist-card kebab menu items.
 *
 * All module state here (picker cleanup, scroll/debounce/init flags) was
 * private to these functions; `_globalSearchActive` is shared -> `htState`.
 */

import { getState } from "./stateBridge";
import type { UserPlaylist } from "./smartPlaylist";

// ── language picker ─────────────────────────────────────────────────────

export interface LangVariant {
  name: string;
  lang?: string;
  count: number;
}

export interface LangPickerHooks {
  esc(s: unknown): string;
  itemNoun: string;
  langToFlag: Record<string, string>;
  langNames: Record<string, string>;
  cleanFolderName(name: string): string;
  playAllIn(name: string): void;
  navigateInto(name: string): void;
}

let _langPickerCleanup: (() => void) | null = null;

export function closeLangPicker(): void {
  if (_langPickerCleanup) {
    _langPickerCleanup();
    _langPickerCleanup = null;
  }
  const old = document.querySelector(".lang-picker-overlay");
  if (old) old.remove();
}

/** Inner HTML of the picker overlay (pure). */
export function langPickerInnerHtml(variants: LangVariant[], playMode: boolean, h: LangPickerHooks): string {
  const heading = playMode ? "Sprache zum Abspielen wählen" : "Sprachversion wählen";
  let inner = '<div class="lang-picker-title">' + h.esc(heading) + "</div>";
  variants.forEach((v) => {
    const flag = v.lang && h.langToFlag[v.lang] ? h.langToFlag[v.lang] : "";
    const label = v.lang && h.langNames[v.lang] ? h.langNames[v.lang] : h.cleanFolderName(v.name);
    const count = v.count + " " + (v.count !== 1 ? h.itemNoun + "s" : h.itemNoun);
    inner +=
      '<button class="lang-picker-item" data-variant-name="' + h.esc(v.name) + '">' +
      (flag ? '<span class="lang-picker-flag">' + flag + "</span>" : "") +
      '<span class="lang-picker-label">' + h.esc(label) + "</span>" +
      '<span class="lang-picker-count">' + count + "</span>" +
      "</button>";
  });
  return inner;
}

export function showLangPicker(card: HTMLElement, variants: LangVariant[], playMode: boolean, h: LangPickerHooks): void {
  closeLangPicker();
  const overlay = document.createElement("div");
  overlay.className = "lang-picker-overlay";
  overlay.innerHTML = langPickerInnerHtml(variants, playMode, h);

  const rect = card.getBoundingClientRect();
  overlay.style.position = "fixed";
  overlay.style.left = Math.max(4, Math.min(rect.left, window.innerWidth - 260)) + "px";
  if (window.innerHeight - rect.bottom > 200) overlay.style.top = rect.bottom + 4 + "px";
  else overlay.style.bottom = window.innerHeight - rect.top + 4 + "px";
  document.body.appendChild(overlay);

  overlay.querySelectorAll<HTMLElement>(".lang-picker-item").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const vName = btn.dataset.variantName || "";
      closeLangPicker();
      if (playMode) h.playAllIn(vName);
      else h.navigateInto(vName);
    });
  });

  const onDocClick = (e: Event) => {
    const t = e.target as Node;
    if (!overlay.contains(t) && !card.contains(t)) closeLangPicker();
  };
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Escape") closeLangPicker();
  };
  document.addEventListener("click", onDocClick, true);
  document.addEventListener("keydown", onKeyDown);
  _langPickerCleanup = () => {
    document.removeEventListener("click", onDocClick, true);
    document.removeEventListener("keydown", onKeyDown);
  };
}

// ── filter-bar scroll reveal ────────────────────────────────────────────

let _fbScrollInitDone = false;
let _fbLastScrollY = 0;

/** Wire (once) the track-view scroll handler that hides/reveals the filter bar. */
export function initFilterBarScrollReveal(filterBar: Element): void {
  if (_fbScrollInitDone) return;
  _fbScrollInitDone = true;
  const wrap = document.getElementById("track-view");
  if (!wrap) return;
  wrap.addEventListener("scroll", () => {
    const y = wrap.scrollTop;
    if (y < 10 || y < _fbLastScrollY - 2) filterBar.classList.remove("fb-scroll-hidden");
    else if (y > _fbLastScrollY + 8) filterBar.classList.add("fb-scroll-hidden");
    _fbLastScrollY = y;
  });
}

// ── global search wiring ────────────────────────────────────────────────

export interface GlobalSearchHooks {
  globalSearch(val: string): void;
  exitGlobalSearch(): void;
}

let _gsDebounce: ReturnType<typeof setTimeout> | null = null;
let _gsListenersInit = false;

/** Show the header search box and wire its events once. */
export function initGlobalSearch(h: GlobalSearchHooks): void {
  const inp = document.getElementById("global-search-input") as HTMLInputElement | null;
  const st = getState();
  if (!inp || !st) return;
  inp.classList.remove("view-hidden");
  if (_gsListenersInit) return;
  _gsListenersInit = true;
  inp.addEventListener("input", () => {
    if (_gsDebounce) clearTimeout(_gsDebounce);
    const val = inp.value.trim();
    if (!val) {
      if (st.globalSearchActive) h.exitGlobalSearch();
      return;
    }
    _gsDebounce = setTimeout(() => h.globalSearch(val), 200);
  });
  inp.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      inp.value = "";
      if (st.globalSearchActive) h.exitGlobalSearch();
      inp.blur();
    }
  });
}

export function hideGlobalSearch(): void {
  const inp = document.getElementById("global-search-input") as HTMLInputElement | null;
  if (inp) {
    inp.classList.add("view-hidden");
    inp.value = "";
  }
}

// ── playlist card kebab menu ────────────────────────────────────────────

export interface CtxMenuItem {
  icon: string;
  label: string;
  danger?: boolean;
  onClick(): void;
}

export interface PlaylistCtxHandlers {
  refresh(plId: string): void;
  editRules(pl: UserPlaylist): void;
  rename(plId: string): void;
  remove(plId: string): void;
  icEdit: string;
  icTrash: string;
}

const IC_REFRESH_SM =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px"><polyline points="23,4 23,10 17,10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>';
const IC_PENCIL_SM =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>';

/** Menu entries for a playlist card (smart playlists get refresh + edit rules). */
export function playlistCtxMenuItems(pl: UserPlaylist, h: PlaylistCtxHandlers): CtxMenuItem[] {
  const items: CtxMenuItem[] = [];
  if (pl.smart && pl.smart.rules) {
    items.push({ icon: IC_REFRESH_SM, label: "Aktualisieren", onClick: () => h.refresh(pl.id) });
    items.push({ icon: h.icEdit, label: "Regeln bearbeiten", onClick: () => h.editRules(pl) });
  }
  items.push({ icon: IC_PENCIL_SM, label: "Umbenennen", onClick: () => h.rename(pl.id) });
  items.push({ icon: h.icTrash, label: "Löschen", danger: true, onClick: () => h.remove(pl.id) });
  return items;
}

