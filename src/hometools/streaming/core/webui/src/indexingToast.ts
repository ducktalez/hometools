/**
 * Indexing toast (library scan in progress). Ported from `_core.py`
 * (`showIndexingToast` / `hideIndexingToast`). Element + per-run dismissal
 * state are module-private. Dismissal persists in localStorage keyed by the
 * run's start time: survives reload, new run shows the toast again.
 */

import { indexingToastHtml } from "./chromeHtml";
import { clearIndexRefreshTimer } from "./catalogFetch";

const DISMISS_KEY = "ht-index-toast-dismissed";

let _el: HTMLElement | null = null;
let _dismissed = false;
let _runId = "";

function dismissedRunId(): string {
  try {
    return localStorage.getItem(DISMISS_KEY) || "";
  } catch {
    return "";
  }
}

export function showIndexingToast(
  msg: string | null | undefined,
  prog: unknown,
  esc: (s: unknown) => string
): void {
  const p = prog as { last_build_started_at?: unknown } | null | undefined;
  const runId = p && p.last_build_started_at != null ? String(p.last_build_started_at) : "";
  _runId = runId;
  if (_dismissed) return;
  if (runId && dismissedRunId() === runId) {
    _dismissed = true;
    return;
  }
  if (!_el) {
    const el = document.createElement("div");
    el.className = "ht-indexing-toast";
    el.title = "Antippen zum Ausblenden";
    el.addEventListener("click", () => {
      _dismissed = true;
      if (_runId) {
        try {
          localStorage.setItem(DISMISS_KEY, _runId);
        } catch {
          /* ignore */
        }
      }
      el.classList.remove("visible");
    });
    document.body.appendChild(el);
    _el = el;
  }
  _el.innerHTML = indexingToastHtml(msg, prog, esc);
  _el.classList.add("visible");
}

export function hideIndexingToast(): void {
  if (_el) _el.classList.remove("visible");
  clearIndexRefreshTimer();
  _dismissed = false;
  try {
    localStorage.removeItem(DISMISS_KEY);
  } catch {
    /* ignore */
  }
}

