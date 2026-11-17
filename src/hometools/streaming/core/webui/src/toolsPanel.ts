/**
 * Tools panel (tool-mode toggles, header split-pill, dupe link) — ported from
 * `player_js/_track_render.py`. Tool state (`ht-tools` in localStorage) is
 * private here; legacy reads it via `toolFlags()` / `anyToolActive()`.
 * Side effects on the rest of the app come in via `ToolsPanelHooks`.
 */

import { getState } from "./stateBridge";
import { ensureDupeIndex, dupeCount } from "./dupeState";

export interface ToolFlags {
  active?: boolean;
  inlineRatings?: boolean;
  downloads?: boolean;
  playlists?: boolean;
  duplicates?: boolean;
  fileMover?: boolean;
  bpmCalc?: boolean;
  autoRefresh?: string;
}

export interface ToolsPanelHooks {
  folderGrid: HTMLElement | null;
  showFolderView(): void;
  applyViewMode(): void;
  applyFilter(force?: boolean): void;
  updatePlayerBarActions(): void;
  /** Legacy `_invalidateDupeMap` (also resets the render guard). */
  invalidateDupeMap(): void;
  refreshCatalog(): void;
  playDuplicates(): void;
  closeDupePanel(): void;
  routerUpdate(): void;
}

const STORAGE_KEY = "ht-tools";
const BODY_CLASSES = [
  "tool-inline-ratings",
  "tool-hide-downloads",
  "tool-hide-playlists",
  "tool-show-duplicates",
  "tool-show-file-mover",
  "tool-bpm-calc",
];

let _state: ToolFlags = loadFlags();
let _hooks: ToolsPanelHooks | null = null;

function loadFlags(): ToolFlags {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

/** Live flags object (read-only by convention). */
export function toolFlags(): ToolFlags {
  return _state;
}

export function anyToolActive(): boolean {
  return !!_state.active && (!!_state.inlineRatings || !!_state.duplicates || !!_state.fileMover);
}

const el = (id: string): HTMLElement | null => document.getElementById(id);

export function isToolsPanelOpen(): boolean {
  const b = el("tools-panel-backdrop");
  return !!b && !b.hasAttribute("hidden");
}

function updateActivateBtn(): void {
  const isOn = !!_state.active;
  const all = el("tools-activate-all");
  if (all) {
    all.textContent = isOn ? "Tool-Modus deaktivieren" : "Tool-Modus aktivieren";
    all.classList.toggle("tools-activate-all--active", isOn);
    all.title = isOn ? "Tool-Modus ausschalten" : "Tool-Modus mit den konfigurierten Einstellungen aktivieren";
  }
  const toggle = el("tools-pill-toggle");
  if (toggle) {
    toggle.classList.toggle("active", isOn);
    toggle.title = isOn ? "Tool-Modus deaktivieren" : "Tool-Modus aktivieren";
  }
  const wrap = el("tools-pill-wrap");
  if (wrap) wrap.classList.toggle("has-active", anyToolActive());
}

function setChecked(id: string, on: boolean): void {
  const cb = el(id) as HTMLInputElement | null;
  if (cb) cb.checked = on;
}

function rerenderCurrentView(h: ToolsPanelHooks): void {
  const st = getState();
  if (h.folderGrid && !h.folderGrid.classList.contains("view-hidden")) {
    h.showFolderView();
  } else if (st && st.inPlaylist) {
    h.applyViewMode();
    h.applyFilter();
  }
}

/** Sync body classes + checkboxes with the flags and re-render the current view. */
export function applyToolState(): void {
  const h = _hooks;
  if (!h) return;
  updateActivateBtn();
  /* Legacy body classes persisted by older versions */
  document.body.classList.remove("tool-refresh-off", "tool-refresh-in-pill");
  const pill = el("tools-pill");
  if (!_state.active) {
    BODY_CLASSES.forEach((c) => document.body.classList.remove(c));
    if (pill) pill.classList.remove("has-active");
    rerenderCurrentView(h);
    return;
  }
  const body = document.body.classList;
  const flag = (cls: string, on: boolean, checkId: string): void => {
    body.toggle(cls, on);
    setChecked(checkId, on);
  };
  flag("tool-inline-ratings", !!_state.inlineRatings, "tool-inline-ratings");
  /* downloads/playlists default to ON; only an explicit false hides them */
  flag("tool-hide-downloads", _state.downloads === false, "tool-downloads");
  setChecked("tool-downloads", _state.downloads !== false);
  flag("tool-hide-playlists", _state.playlists === false, "tool-playlists");
  setChecked("tool-playlists", _state.playlists !== false);
  flag("tool-show-duplicates", !!_state.duplicates, "tool-duplicates");
  flag("tool-show-file-mover", !!_state.fileMover, "tool-file-mover");
  flag("tool-bpm-calc", !!_state.bpmCalc, "tool-bpm-calc");
  const any = anyToolActive();
  el("tools-pill-wrap")?.classList.toggle("has-active", any);
  if (pill) pill.classList.toggle("has-active", any);
  rerenderCurrentView(h);
  h.updatePlayerBarActions();
}

function saveToolState(): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(_state));
  } catch {
    /* quota / private mode */
  }
  applyToolState();
}

export function openToolsPanel(): void {
  const h = _hooks;
  const backdrop = el("tools-panel-backdrop");
  if (backdrop) backdrop.removeAttribute("hidden");
  const st = getState();
  const link = el("dupe-show-link");
  /* Always show dupe count when panel opens — even if the toggle is off */
  if (link && st && st.allItems.length > 0) {
    const dc = dupeCount(st.allItems);
    link.textContent =
      dc > 0 ? dc + " Duplikat-Gruppe" + (dc !== 1 ? "n" : "") + " \u2014 Liste anzeigen" : "Keine Duplikate gefunden";
    link.style.display = "inline-block";
  }
  if (h) h.routerUpdate();
}

export function closeToolsPanel(): void {
  const backdrop = el("tools-panel-backdrop");
  if (backdrop) backdrop.setAttribute("hidden", "");
  if (_hooks) _hooks.routerUpdate();
}

/** Prepare/release the dupe index when the tool mode or the dupes toggle changes. */
function syncDupeIndex(h: ToolsPanelHooks): void {
  const st = getState();
  if (_state.active && _state.duplicates && st) ensureDupeIndex(st.allItems);
  if (!_state.active) h.invalidateDupeMap();
}

function toggleActive(h: ToolsPanelHooks): void {
  _state.active = !_state.active;
  syncDupeIndex(h);
  saveToolState();
  const st = getState();
  if (st && st.inPlaylist) h.applyFilter();
}

/** Bind a checkbox to one flag; re-render the track list afterwards. */
function bindFlag(id: string, key: "inlineRatings" | "downloads" | "playlists" | "fileMover" | "bpmCalc", rerender: boolean): void {
  const cb = el(id) as HTMLInputElement | null;
  if (!cb) return;
  cb.addEventListener("change", () => {
    _state[key] = cb.checked;
    saveToolState();
    const st = getState();
    if (rerender && st && st.inPlaylist && _hooks) _hooks.applyFilter();
  });
}

let _initialized = false;

export function initToolsPanel(h: ToolsPanelHooks): void {
  _hooks = h;
  if (_initialized) {
    applyToolState();
    return;
  }
  _initialized = true;

  el("tools-pill")?.addEventListener("click", openToolsPanel);
  el("tools-pill-toggle")?.addEventListener("click", (e) => {
    e.stopPropagation(); /* don't bubble to tools-pill-wrap / tools-pill */
    toggleActive(h);
  });
  el("tools-panel-close")?.addEventListener("click", closeToolsPanel);
  const backdrop = el("tools-panel-backdrop");
  backdrop?.addEventListener("click", (e) => {
    if (e.target === backdrop) closeToolsPanel();
  });

  el("dupe-panel-close")?.addEventListener("click", h.closeDupePanel);
  el("dupe-panel-play-all")?.addEventListener("click", h.playDuplicates);
  const dupeBackdrop = el("dupe-panel-backdrop");
  dupeBackdrop?.addEventListener("click", (e) => {
    if (e.target === dupeBackdrop) h.closeDupePanel();
  });

  bindFlag("tool-inline-ratings", "inlineRatings", true);
  bindFlag("tool-downloads", "downloads", false);
  bindFlag("tool-playlists", "playlists", false);
  bindFlag("tool-file-mover", "fileMover", true);
  bindFlag("tool-bpm-calc", "bpmCalc", true);

  const dup = el("tool-duplicates") as HTMLInputElement | null;
  dup?.addEventListener("change", () => {
    _state.duplicates = dup.checked;
    const st = getState();
    if (dup.checked) {
      if (st) ensureDupeIndex(st.allItems);
    } else {
      h.invalidateDupeMap();
    }
    saveToolState();
    if (st && st.inPlaylist) h.applyFilter();
  });

  el("dupe-show-link")?.addEventListener("click", (e) => {
    e.preventDefault();
    closeToolsPanel();
    h.playDuplicates();
  });
  el("tools-global-refresh-btn")?.addEventListener("click", () => {
    closeToolsPanel();
    h.refreshCatalog();
  });
  el("tools-activate-all")?.addEventListener("click", () => toggleActive(h));

  applyToolState();
}

/** Test hook: reset module state. */
export function _resetToolsPanelForTest(): void {
  _state = loadFlags();
  _hooks = null;
  _initialized = false;
}

