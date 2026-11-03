/**
 * Playback-progress helpers. Ported from `player_js/_core.py`
 * (`_progressApiBase`, guard + payload of `saveProgressNow`).
 * Pure helpers first; below them the stateful save/load chain
 * (`_progressRelPath` + debounce timer are module-private; legacy uses
 * `getProgressPath`/`setProgressPath`/`cancelProgressTimer`).
 */

/** `/api/<x>/items` -> `/api/<x>/progress`. */
export function progressApiBase(apiPath: string): string {
  return apiPath.substring(0, apiPath.lastIndexOf("/")) + "/progress";
}

/**
 * JSON body for a server progress save, or null when the save must be
 * skipped (no path, non-finite values, first/last 5 s).
 */
export function buildProgressPayload(rp: string, pos: number, dur: number): string | null {
  if (!rp) return null;
  if (!isFinite(pos) || !isFinite(dur)) return null;
  if (pos < 5 || pos > dur - 5) return null;
  return JSON.stringify({ relative_path: rp, position_seconds: pos, duration: dur });
}


export interface ProgressHooks {
  player: HTMLMediaElement;
  /** `API_PATH` (items endpoint). */
  apiPath: string;
  saveLastPlayedLocal(rp: string, pos: number): void;
  showToast(msg: string, durationMs?: number): void;
  fmtTime(s: number): string;
}
let _relPath = "";
let _timer: ReturnType<typeof setTimeout> | null = null;
export function getProgressPath(): string {
  return _relPath;
}
export function setProgressPath(rp: string): void {
  _relPath = rp || "";
}
export function cancelProgressTimer(): void {
  if (_timer) {
    clearTimeout(_timer);
    _timer = null;
  }
}
/** Persist current position (localStorage always; server unless in first/last 5 s). */
export function saveProgressNow(h: ProgressHooks): void {
  const rp = _relPath;
  if (!rp) return;
  const pos = h.player.currentTime;
  const dur = h.player.duration;
  if (!isFinite(pos) || !isFinite(dur)) return;
  h.saveLastPlayedLocal(rp, pos);
  const payload = buildProgressPayload(rp, pos, dur);
  if (!payload) return;
  const url = progressApiBase(h.apiPath);
  /* sendBeacon survives page unload / mobile backgrounding. */
  if (typeof navigator !== "undefined" && navigator.sendBeacon) {
    try {
      if (navigator.sendBeacon(url, new Blob([payload], { type: "application/json" }))) return;
    } catch {
      /* fall through to fetch */
    }
  }
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload,
    keepalive: true,
  }).catch(() => {});
}
export function saveProgressDebounced(h: ProgressHooks): void {
  cancelProgressTimer();
  _timer = setTimeout(() => saveProgressNow(h), 5000);
}
export function clearProgressFor(rp: string, h: ProgressHooks): void {
  if (!rp) return;
  fetch(progressApiBase(h.apiPath), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ relative_path: rp, position_seconds: 0, duration: 0 }),
  }).catch(() => {});
}
/** Fetch server progress for `rp` and seek there once metadata is known. */
export function loadAndSeekProgress(rp: string, h: ProgressHooks): void {
  if (!rp) return;
  fetch(progressApiBase(h.apiPath) + "?path=" + encodeURIComponent(rp))
    .then((r) => (r.ok ? r.json() : null))
    .then((data: { items?: Array<{ position_seconds?: number }> } | null) => {
      if (!data || !data.items || !data.items.length) return;
      const pos = data.items[0].position_seconds || 0;
      if (pos < 5) return;
      const p = h.player;
      const doSeek = (): void => {
        if (isFinite(p.duration) && pos < p.duration - 5) {
          p.currentTime = pos;
          h.showToast("Fortfahren bei " + h.fmtTime(pos), 3000);
        }
      };
      if (isFinite(p.duration) && p.duration > 0) doSeek();
      else p.addEventListener("loadedmetadata", doSeek, { once: true });
    })
    .catch(() => {});
}
