/**
 * Player-bar control state views. Ported from `player_js/_library_tools.py`
 * (cycleShuffle/cycleRepeat mode transitions, updateShuffleBtn/
 * updateRepeatBtn labels, renderPlayerRating star data, rating-bar width).
 * Pure: modes/icons explicit params. DOM writes, localStorage and queue
 * rebuilds stay legacy.
 */
export type ShuffleModeValue = false | "normal" | "weighted";
export type RepeatModeValue = false | "all" | "one";
/** off -> normal -> weighted -> off */
export function nextShuffleMode(mode: unknown): ShuffleModeValue {
  if (!mode) return "normal";
  if (mode === "normal") return "weighted";
  return false;
}
/** off -> all -> one -> off */
export function nextRepeatMode(mode: unknown): RepeatModeValue {
  if (!mode) return "all";
  if (mode === "all") return "one";
  return false;
}
export interface ToggleBtnView {
  active: boolean;
  /** extra modifier class state (weighted shuffle / repeat one) */
  variant: boolean;
  title: string;
}
export function shuffleBtnView(mode: unknown): ToggleBtnView {
  return {
    active: !!mode,
    variant: mode === "weighted",
    title:
      mode === "weighted"
        ? "Shuffle (gewichtet nach Bewertung) \u2014 Long Press f\u00fcr Aus"
        : mode === "normal"
          ? "Shuffle (zuf\u00e4llig) \u2014 Klick f\u00fcr gewichtet, Long Press f\u00fcr Aus"
          : "Shuffle aktivieren",
  };
}
export function repeatBtnView(mode: unknown): ToggleBtnView {
  return {
    active: !!mode,
    variant: mode === "one",
    title:
      mode === "one"
        ? "Einzeltitel wiederholen \u2014 Klick f\u00fcr Aus"
        : mode === "all"
          ? "Alle wiederholen \u2014 Klick f\u00fcr Einzeltitel"
          : "Wiederholen aktivieren",
  };
}
export interface RatingStarView {
  star: number;
  active: boolean;
  title: string;
}
/** Five player-bar star buttons for `stars` (rounded). */
export function playerRatingStars(stars: number | null | undefined): RatingStarView[] {
  const rounded = Math.round(stars || 0);
  const out: RatingStarView[] = [];
  for (let i = 1; i <= 5; i++) {
    out.push({
      star: i,
      active: i <= rounded,
      title:
        i === rounded && rounded > 0
          ? "Bewertung entfernen (nochmals klicken)"
          : i + (i === 1 ? " Stern" : " Sterne"),
    });
  }
  return out;
}
/** Width in percent of the thumbnail rating bar; 0 = remove bar. */
export function ratingBarWidthPct(rating: number | null | undefined): number {
  const r = rating || 0;
  return r > 0 ? (r / 5) * 100 : 0;
}
/** Five edit-modal star buttons for `stars` (rounded); also the stored value. */
export function editModalRatingStars(stars: number | null | undefined): { rounded: number; stars: RatingStarView[] } {
  const rounded = Math.round(stars || 0);
  const out: RatingStarView[] = [];
  for (let i = 1; i <= 5; i++) {
    out.push({ star: i, active: i <= rounded, title: i + (i === 1 ? " Stern" : " Sterne") });
  }
  return { rounded, stars: out };
}
/** Clicking the already-selected star clears the rating (0). */
export function toggleEditRating(clicked: number, current: number): number {
  return clicked === current ? 0 : clicked;
}
export function favoriteBtnView(pinned: boolean): { pinned: boolean; title: string } {
  return { pinned, title: pinned ? "Favorit entfernen" : "Favorit" };
}