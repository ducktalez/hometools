/**
 * BPM adjust popup (Tools-panel "BPM berechnen") — ported from
 * `player_js/_track_render.py` (_openBpmAdjustMenu, _closeBpmAdjustMenu,
 * _patchAllItemsBpm). Cleanup handle private. State via htState; paths,
 * icons and toast via `BpmMenuHooks`.
 */

import { getState } from "./stateBridge";
import { replaceItemFields } from "./catalogQuery";
import { bpmAdjustMenuHtml, type BpmMenuIcons } from "./playerBarHtml";
import { renderBpmPill } from "./metricPill";

export interface BpmMenuHooks {
  calcPath: string;
  adjustPath: string;
  setPath: string;
  bpmMin: number;
  bpmMax: number;
  icons: BpmMenuIcons;
  /** Tools-panel "BPM berechnen" active (pill gets clickable variant). */
  calcEnabled(): boolean;
  toast(msg: string): void;
}

interface BpmResult {
  ok?: boolean;
  bpm: number;
  error?: string;
}

let _cleanup: (() => void) | null = null;

export function closeBpmAdjustMenu(): void {
  if (_cleanup) {
    _cleanup();
    _cleanup = null;
  }
  const old = document.getElementById("bpm-adjust-menu");
  if (old) old.remove();
}

/** langsamer/schneller halves/doubles the value; server biases future recalculations. */
export function openBpmAdjustMenu(idx: number, btnEl: HTMLElement, h: BpmMenuHooks): void {
  closeBpmAdjustMenu();
  const st = getState();
  if (!st) return;
  const t = st.filteredItems[idx];
  if (!t || !t.relative_path) return;
  const path = t.relative_path;

  const menu = document.createElement("div");
  menu.id = "bpm-adjust-menu";
  menu.className = "ht-ctx-menu bpm-adjust-menu";
  menu.innerHTML = bpmAdjustMenuHtml(t.bpm || 0, h.icons);
  document.body.appendChild(menu);

  const rect = btnEl.getBoundingClientRect();
  menu.style.right = Math.max(4, window.innerWidth - rect.right) + "px";
  if (window.innerHeight - rect.bottom >= menu.offsetHeight + 8) {
    menu.style.top = rect.bottom + 4 + "px";
  } else {
    menu.style.top = Math.max(4, rect.top - menu.offsetHeight - 4) + "px";
  }

  const busy = (isBusy: boolean): void => {
    menu.querySelectorAll<HTMLButtonElement | HTMLInputElement>("button, input").forEach((el) => {
      el.disabled = isBusy;
    });
  };

  const applyResult = (d: BpmResult | null, fallbackErr: string): void => {
    busy(false);
    if (!d || !d.ok) {
      h.toast((d && d.error) || fallbackErr);
      return;
    }
    t.bpm = d.bpm;
    replaceItemFields([st.allItems], path, { bpm: d.bpm });
    if (btnEl.parentNode) {
      const wrap = document.createElement("span");
      wrap.innerHTML = renderBpmPill(d.bpm, h.bpmMin, h.bpmMax, {
        index: idx,
        relativePath: path,
        calcEnabled: h.calcEnabled(),
      });
      const pill = wrap.firstChild;
      if (pill) btnEl.parentNode.replaceChild(pill, btnEl);
    }
    h.toast("BPM: " + Math.round(d.bpm));
    closeBpmAdjustMenu();
  };

  const post = (url: string, body: object, failMsg: string, netMsg: string): void => {
    busy(true);
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: BpmResult | null) => applyResult(d, failMsg))
      .catch(() => {
        busy(false);
        h.toast(netMsg);
      });
  };

  menu.querySelector('[data-action="reload"]')?.addEventListener("click", () => {
    post(h.calcPath, { path }, "BPM-Berechnung fehlgeschlagen", "BPM-Berechnung fehlgeschlagen (Netzwerkfehler)");
  });

  (["slower", "faster"] as const).forEach((action) => {
    const btn = menu.querySelector<HTMLButtonElement>('[data-action="' + action + '"]');
    if (!btn) return;
    btn.addEventListener("click", () => {
      if (btn.disabled) return;
      post(
        h.adjustPath,
        { path, factor: action === "slower" ? 0.5 : 2 },
        "Anpassung fehlgeschlagen",
        "Anpassung fehlgeschlagen (Netzwerkfehler)"
      );
    });
  });

  const manualInput = menu.querySelector<HTMLInputElement>(".bpm-adjust-input");
  const applyBtn = menu.querySelector<HTMLElement>(".bpm-adjust-apply");
  const submitManual = (): void => {
    const val = manualInput ? parseFloat(manualInput.value) : NaN;
    if (!val || val <= 0) {
      h.toast("Bitte einen g\u00fcltigen BPM-Wert eingeben");
      return;
    }
    post(h.setPath, { path, bpm: val }, "Speichern fehlgeschlagen", "Speichern fehlgeschlagen (Netzwerkfehler)");
  };
  applyBtn?.addEventListener("click", submitManual);
  if (manualInput) {
    manualInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        submitManual();
      }
    });
    manualInput.addEventListener("click", (e) => e.stopPropagation());
  }

  const onOutside = (e: Event): void => {
    const target = e.target as Node;
    if (!menu.contains(target) && target !== btnEl && !btnEl.contains(target)) closeBpmAdjustMenu();
  };
  const onEsc = (e: KeyboardEvent): void => {
    if (e.key === "Escape") closeBpmAdjustMenu();
  };
  setTimeout(() => {
    document.addEventListener("click", onOutside);
    document.addEventListener("keydown", onEsc);
  }, 0);
  _cleanup = () => {
    document.removeEventListener("click", onOutside);
    document.removeEventListener("keydown", onEsc);
  };
}

