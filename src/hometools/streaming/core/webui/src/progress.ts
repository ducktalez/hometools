/**
 * Playback-progress helpers. Ported from `player_js/_core.py`
 * (`_progressApiBase`, guard + payload of `saveProgressNow`).
 * Pure: `apiPath` and player values are explicit params. Timers/fetch/
 * sendBeacon stay legacy (touch `player`, `_progressRelPath`).
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

