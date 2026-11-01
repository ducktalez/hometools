/**
 * Duplicate panel (open/close/wiring + item collection) — ported from
 * `player_js/_library_tools.py` (openDupePanel, closeDupePanel,
 * playDuplicates' collection step). Dupe state (`_dupeMap` etc.) stays in
 * legacy (read by track rendering) and is passed in; actions via hooks.
 */

import { dupePanelBodyHtml } from "./panelBodies";

type Item = { relative_path?: string; [k: string]: unknown };
type DupeMap = Record<string, number[]>;

export interface DupePanelData {
  allItems: Item[];
  dupeMap: DupeMap;
  dupeSafety: Record<string, boolean> | null;
  dupePaths: Set<string> | null;
}

export interface DupePanelHooks {
  escHtml(s: unknown): string;
  filePlaceholder: string;
  icDuplicate: string;
  icTrash: string;
  /** Trash button: delete allItems[index]. */
  deleteDuplicate(allIndex: number): void;
  /** Row click: panel already closed; navigate + play. */
  playItem(item: Item): void;
}

export function closeDupePanel(): void {
  const backdrop = document.getElementById("dupe-panel-backdrop");
  if (backdrop) backdrop.setAttribute("hidden", "");
}

export function dupeSubtitle(groups: number, files: number): string {
  return groups + " Duplikat-Gruppe" + (groups !== 1 ? "n" : "") + " (" + files + " Dateien)";
}

/** All items of all groups, group by group (natural listening order). */
export function collectDupeItems(dupeMap: DupeMap, allItems: Item[]): Item[] {
  const out: Item[] = [];
  Object.keys(dupeMap).forEach((key) => {
    dupeMap[key].forEach((idx) => {
      const t = allItems[idx];
      if (t) out.push(t);
    });
  });
  return out;
}

export function openDupePanel(d: DupePanelData, h: DupePanelHooks): void {
  const backdrop = document.getElementById("dupe-panel-backdrop");
  const body = document.getElementById("dupe-panel-body");
  if (!backdrop || !body) return;
  const keys = Object.keys(d.dupeMap);
  body.innerHTML = dupePanelBodyHtml(d.allItems as never, d.dupeMap, d.dupeSafety as never, {
    escHtml: h.escHtml,
    filePlaceholder: h.filePlaceholder,
    icDuplicate: h.icDuplicate,
    icTrash: h.icTrash,
  } as never);
  if (keys.length > 0) {
    body.querySelectorAll<HTMLElement>(".dupe-trash-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        h.deleteDuplicate(Number(btn.dataset.allIndex));
      });
    });
    body.querySelectorAll<HTMLElement>(".dupe-group-item").forEach((el) => {
      el.addEventListener("click", () => {
        const t = d.allItems[Number(el.dataset.allIndex)];
        if (!t) return;
        closeDupePanel();
        h.playItem(t);
      });
    });
  }
  const sub = document.getElementById("dupe-panel-subtitle");
  if (sub) sub.textContent = dupeSubtitle(keys.length, d.dupePaths ? d.dupePaths.size : 0);
  backdrop.removeAttribute("hidden");
}

