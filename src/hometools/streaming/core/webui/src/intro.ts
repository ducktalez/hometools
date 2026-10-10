/**
 * Skip-Intro pure helpers.
 *
 * Ported from `player_js/_core.py` (`_setCurrentIntro` parse half,
 * `_updateSkipIntroBtn` mode decision, `_patchIntroLocal`). DOM updates,
 * fetch and IIFE state vars (`_introStart`/`_introEnd`/`_curIsSeries`/
 * `_introBtnMode`) stay in `_core.py`. Explicit params, no window reads.
 */

export type IntroBtnMode = "" | "skip" | "set";

export interface IntroInfo {
  start: number;
  end: number;
  isSeries: boolean;
}

/** Intro markers + series flag of an item. Missing/invalid → 0/false. */
export function parseIntro(t: LegacyMediaItem | null | undefined): IntroInfo {
  if (!t) return { start: 0, end: 0, isSeries: false };
  const start = Math.max(0, parseFloat(String(t.intro_start)) || 0);
  const end = Math.max(0, parseFloat(String(t.intro_end)) || 0);
  const isSeries = (parseInt(String(t.season), 10) || 0) > 0 || (parseInt(String(t.episode), 10) || 0) > 0;
  return { start, end, isSeries };
}

/**
 * Which skip-intro button mode applies at playback position `cur`.
 * - "skip": marker set, inside [start, end - 0.3)
 * - "set":  no marker, series episode, 5s..min(25% dur, 180s)
 * - "":     hide button
 */
export function introButtonMode(
  cur: number,
  dur: number,
  start: number,
  end: number,
  isSeries: boolean
): IntroBtnMode {
  if (end > 0 && cur >= start && cur < end - 0.3) return "skip";
  if (end <= 0 && isSeries && dur > 0) {
    const maxSet = Math.min(dur * 0.25, 180);
    if (cur >= 5 && cur <= maxSet) return "set";
  }
  return "";
}

/**
 * Write new markers onto every item with `relPath` in the given arrays.
 * Mutates in place on purpose — legacy arrays share item objects, so the
 * updated marker must be visible everywhere without a re-fetch.
 */
export function patchIntroLocal(
  arrays: Array<LegacyMediaItem[] | null | undefined>,
  relPath: string,
  start: number,
  end: number
): void {
  if (!relPath) return;
  arrays.forEach((arr) => {
    if (!arr) return;
    for (let i = 0; i < arr.length; i++) {
      const it = arr[i];
      if (it && it.relative_path === relPath) {
        it.intro_start = start;
        it.intro_end = end;
      }
    }
  });
}

