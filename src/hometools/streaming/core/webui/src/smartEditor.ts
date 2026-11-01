/**
 * Smart-playlist editor modal (state + DOM wiring + save) — ported from
 * `player_js/_smart_playlists.py` (openSmartPlaylistEditor, _smartRenderEditor,
 * _smartWireEditor, _smartCollectFromDom, _smartSubmit).
 *
 * `_smartEditorState` was private to those functions -> module state here.
 * Playlists via `htState.userPlaylists`; everything view-ish (esc, icon,
 * toast, re-render root, API path) comes in through `SmartEditorHooks`.
 */

import { getState } from "./stateBridge";
import { smartEditorModalHtml } from "./smartEditorModal";
import { smartFieldType, smartOpsFor, buildSmartSubmit } from "./smartPlaylist";
import type { SmartEditorState, UserPlaylist } from "./smartPlaylist";

export interface SmartEditorHooks {
  /** `PLAYLISTS_SMART_PATH` */
  apiPath: string;
  esc(s: unknown): string;
  /** `IC_SMART_PLAYLIST` markup */
  icon: string;
  toast(msg: string): void;
  showFolderView(): void;
}

let _state: SmartEditorState | null = null;

const NEW_RULE = () => ({ field: "rating", op: "gte", value: 4 as unknown });

function lists(): UserPlaylist[] {
  const st = getState();
  return st ? (st.userPlaylists as UserPlaylist[]) : [];
}

/** Current editor state (null when closed). Test/debug aid. */
export function getEditorState(): SmartEditorState | null {
  return _state;
}

export function openSmartPlaylistEditor(existing: UserPlaylist | null, h: SmartEditorHooks): void {
  if (existing && existing.smart) {
    _state = {
      id: existing.id,
      name: existing.name || "",
      match: existing.smart.match || "all",
      rules: JSON.parse(JSON.stringify(existing.smart.rules || [])),
      limit: existing.smart.limit || "",
    };
  } else {
    _state = { id: null, name: "", match: "all", rules: [NEW_RULE()], limit: "" };
  }
  render(h);
}

function render(h: SmartEditorHooks): void {
  if (!_state) return;
  const html = smartEditorModalHtml(_state, lists(), h.esc, h.icon);
  const existing = document.getElementById("smart-editor-backdrop");
  if (existing) existing.remove();
  document.body.insertAdjacentHTML("beforeend", html);
  wire(h);
}

function defaultValueFor(field: string): unknown {
  const t = smartFieldType(field);
  return t === "playlist" ? [] : t === "bool" ? true : t === "number" ? 0 : "";
}

function wire(h: SmartEditorHooks): void {
  const bd = document.getElementById("smart-editor-backdrop");
  if (!bd) return;
  const close = () => {
    bd.remove();
    _state = null;
  };
  const sync = () => collectFromDom(document);
  bd.addEventListener("click", (e) => {
    if (e.target === bd) close();
  });
  document.getElementById("smart-editor-close")?.addEventListener("click", close);
  document.getElementById("smart-editor-cancel")?.addEventListener("click", close);
  document.getElementById("smart-editor-add-rule")?.addEventListener("click", () => {
    sync();
    if (!_state) return;
    _state.rules.push(NEW_RULE());
    render(h);
  });
  bd.querySelectorAll<HTMLInputElement>('input[name="smart-match"]').forEach((r) => {
    r.addEventListener("change", () => {
      sync();
      if (_state) _state.match = r.value as "all" | "any";
    });
  });
  bd.querySelectorAll<HTMLElement>(".smart-rule-row").forEach((row) => {
    const idx = Number(row.dataset.idx);
    row.querySelector(".smart-rule-field")?.addEventListener("change", (e) => {
      sync();
      const rule = _state && _state.rules[idx];
      if (!rule) return;
      rule.field = (e.target as HTMLSelectElement).value;
      rule.op = smartOpsFor(rule.field)[0][0];
      rule.value = defaultValueFor(rule.field);
      render(h);
    });
    row.querySelector(".smart-rule-op")?.addEventListener("change", (e) => {
      sync();
      if (!_state || !_state.rules[idx]) return;
      _state.rules[idx].op = (e.target as HTMLSelectElement).value;
      render(h);
    });
    row.querySelector(".smart-rule-del")?.addEventListener("click", () => {
      sync();
      if (!_state) return;
      _state.rules.splice(idx, 1);
      if (_state.rules.length === 0) _state.rules.push(NEW_RULE());
      render(h);
    });
  });
  document.getElementById("smart-editor-save")?.addEventListener("click", () => {
    sync();
    submit(h, close);
  });
}

/** Read the modal's inputs back into the editor state. */
export function collectFromDom(doc: Document): void {
  const s = _state;
  if (!s) return;
  const nameEl = doc.getElementById("smart-editor-name") as HTMLInputElement | null;
  const limitEl = doc.getElementById("smart-editor-limit") as HTMLInputElement | null;
  if (nameEl) s.name = nameEl.value.trim();
  if (limitEl) s.limit = limitEl.value ? Number(limitEl.value) : "";
  const matched = doc.querySelector('input[name="smart-match"]:checked') as HTMLInputElement | null;
  if (matched) s.match = matched.value as "all" | "any";
  doc.querySelectorAll<HTMLElement>(".smart-rule-row").forEach((row) => {
    const rule = s.rules[Number(row.dataset.idx)];
    if (!rule) return;
    const val = (sel: string) => (row.querySelector(sel) as HTMLInputElement).value;
    rule.field = val(".smart-rule-field");
    rule.op = val(".smart-rule-op");
    const type = smartFieldType(rule.field);
    if (type === "playlist") {
      rule.value = Array.from(row.querySelectorAll<HTMLInputElement>(".smart-rule-pl-cb"))
        .filter((cb) => cb.checked)
        .map((cb) => cb.value);
    } else if (type === "bool") {
      rule.value = val(".smart-rule-value") === "true";
    } else if (rule.op === "between") {
      rule.value = [Number(val(".smart-rule-value-lo") || 0), Number(val(".smart-rule-value-hi") || 0)];
    } else {
      const v = val(".smart-rule-value");
      rule.value = type === "number" ? Number(v || 0) : v;
    }
  });
}

function submit(h: SmartEditorHooks, onSuccess: () => void): void {
  const s = _state;
  if (!s) return;
  const req = buildSmartSubmit(s);
  if ("error" in req) {
    h.toast(req.error);
    return;
  }
  fetch(h.apiPath, {
    method: req.method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req.payload),
  })
    .then((r) => {
      if (!r.ok) return r.json().then((d) => { throw new Error(d.detail || "Fehler"); });
      return r.json();
    })
    .then((d) => {
      if (!d.playlist) return;
      const l = lists();
      if (s.id) {
        const i = l.findIndex((p) => p.id === s.id);
        if (i >= 0) l[i] = d.playlist;
      } else {
        l.unshift(d.playlist);
      }
      onSuccess();
      h.showFolderView();
      h.toast("Intelligente Playlist gespeichert");
    })
    .catch((err) => h.toast(String((err && err.message) || "Fehler beim Speichern")));
}

