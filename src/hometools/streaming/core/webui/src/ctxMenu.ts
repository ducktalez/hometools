/**
 * Generic kebab/context dropdown + "reveal in explorer" — ported from
 * `player_js/_library_tools.py` (_closeCtxMenu, _openCtxMenu,
 * _revealInExplorer). `_ctxMenuCleanup` is module-private (no other
 * fragment read it). Markup via panelBodies.ts::ctxMenuHtml.
 */

import { ctxMenuHtml } from "./panelBodies";

export interface CtxItem {
  label: string;
  icon?: string;
  danger?: boolean;
  onClick?: () => void;
}

type Esc = (s: unknown) => string;

let cleanup: (() => void) | null = null;

export function closeCtxMenu(): void {
  if (cleanup) {
    cleanup();
    cleanup = null;
  }
  const old = document.getElementById("ht-ctx-menu");
  if (old) old.remove();
}

/** Dropdown anchored right-aligned below `btn` (above if no room). */
export function openCtxMenu(btn: HTMLElement, items: CtxItem[], esc: Esc): void {
  closeCtxMenu();
  const menu = document.createElement("div");
  menu.id = "ht-ctx-menu";
  menu.className = "ht-ctx-menu";
  menu.innerHTML = ctxMenuHtml(items, esc);
  document.body.appendChild(menu);

  const rect = btn.getBoundingClientRect();
  menu.style.right = Math.max(4, window.innerWidth - rect.right) + "px";
  const spaceBelow = window.innerHeight - rect.bottom;
  if (spaceBelow >= menu.offsetHeight + 8) {
    menu.style.top = rect.bottom + 4 + "px";
  } else {
    menu.style.top = Math.max(4, rect.top - menu.offsetHeight - 4) + "px";
  }

  menu.querySelectorAll<HTMLElement>(".ht-ctx-item").forEach((el) => {
    el.addEventListener("click", () => {
      const idx = Number(el.dataset.idx);
      closeCtxMenu();
      const it = items[idx];
      if (it && typeof it.onClick === "function") it.onClick();
    });
  });

  const onOutside = (e: Event): void => {
    const t = e.target as Node | null;
    if (t && !menu.contains(t) && t !== btn && !btn.contains(t)) closeCtxMenu();
  };
  const onEsc = (e: KeyboardEvent): void => {
    if (e.key === "Escape") closeCtxMenu();
  };
  setTimeout(() => {
    document.addEventListener("click", onOutside);
    document.addEventListener("keydown", onEsc);
  }, 0);
  cleanup = () => {
    document.removeEventListener("click", onOutside);
    document.removeEventListener("keydown", onEsc);
  };
}

export interface RevealHooks {
  apiPath: string;
  toast(msg: string): void;
}

/** POST /reveal; toast result. Never throws. */
export function revealInExplorer(relativePath: string, h: RevealHooks): Promise<void> {
  return fetch(h.apiPath, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: relativePath }),
  })
    .then((r) => (r.ok ? r.json() : null))
    .then((d: { revealed?: boolean; path?: string } | null) => {
      if (!d) {
        h.toast("Pfad nicht gefunden");
        return;
      }
      h.toast(d.revealed ? "Explorer ge\u00f6ffnet" : "Pfad: " + d.path);
    })
    .catch(() => h.toast("Fehler beim Anzeigen"));
}

