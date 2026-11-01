/**
 * Inline title/artist edit save (table/detail view) — ported from
 * `player_js/_search_filter.py::_saveInlineTableEdit`. Reuses the metadata
 * edit endpoint; reverts the cell on error or Escape-cancel. `filteredItems`/
 * `allItems` via `htState`.
 */

import { getState } from "./stateBridge";

export interface InlineEditHooks {
  /** `METADATA_EDIT_PATH` */
  editPath: string;
  toast(msg: string): void;
}

/** Collapse whitespace runs and trim (cell text -> value). */
export function normalizeCellText(s: string | null): string {
  return (s || "").replace(/\s+/g, " ").trim();
}

export function saveInlineTableEdit(editable: HTMLElement, h: InlineEditHooks): void {
  const field = editable.dataset.field;
  const rp = editable.dataset.relativePath;
  if (!field || !rp) return;
  const cancelled = editable.dataset.cancelled === "1";
  delete editable.dataset.cancelled;
  const st = getState();
  const rec = (it: LegacyMediaItem) => it.relative_path === rp;
  const t = (st && (st.filteredItems.find(rec) || (st.allItems || []).find(rec))) as Record<string, unknown> | undefined;
  const oldVal = t ? String(t[field] || "") : "";
  const newVal = normalizeCellText(editable.textContent);
  if (cancelled || newVal === oldVal) {
    editable.textContent = oldVal;
    return;
  }
  if (!newVal) {
    editable.textContent = oldVal;
    h.toast("Feld darf nicht leer sein");
    return;
  }
  const payload: Record<string, string> = { path: rp };
  payload[field] = newVal;
  fetch(h.editPath, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => {
      if (!d || !d.ok) {
        editable.textContent = oldVal;
        h.toast("Fehler beim Speichern");
        return;
      }
      if (t) t[field] = newVal;
      editable.textContent = newVal;
      h.toast("Gespeichert");
    })
    .catch(() => {
      editable.textContent = oldVal;
      h.toast("Fehler beim Speichern");
    });
}

