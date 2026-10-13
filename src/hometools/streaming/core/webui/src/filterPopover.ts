/**
 * Filter-popover markup. Ported from `player_js/_search_filter.py`
 * (`_filterPopoverBodyHtml`). Pure: filter state, genre list, star icons and
 * escHtml are explicit params (legacy IIFE vars / main.ts). Wiring
 * (`_wireFilterPopoverBody`) stays legacy — it mutates filter state.
 */
export interface FilterPopoverState {
  rating: number;
  fav: boolean;
  genre: string;
}
export interface FilterPopoverIcons {
  starFilled: string;
  starEmpty: string;
}
export function filterPopoverBodyHtml(
  genreList: string[],
  state: FilterPopoverState,
  icons: FilterPopoverIcons,
  escHtml: (s: unknown) => string
): string {
  let starsHtml = "";
  for (let i = 1; i <= 5; i++) {
    starsHtml +=
      '<button type="button" class="filter-popover-star' + (i <= state.rating ? " active" : "") +
      '" data-star="' + i + '" title="' + i + (i === 1 ? "+ Stern" : "+ Sterne") + '">' +
      (i <= state.rating ? icons.starFilled : icons.starEmpty) + "</button>";
  }
  const genreSectionHtml = genreList.length
    ? '<div class="filter-popover-section">' +
      '<div class="filter-popover-label">Genre</div>' +
      '<select class="filter-popover-genre-select" id="filter-popover-genre-select">' +
      '<option value="">Alle Genres</option>' +
      genreList
        .map((g) => '<option value="' + escHtml(g) + '"' + (g === state.genre ? " selected" : "") + ">" + escHtml(g) + "</option>")
        .join("") +
      "</select>" +
      "</div>"
    : "";
  return (
    '<div class="filter-popover-section">' +
    '<div class="filter-popover-label">Bewertung</div>' +
    '<div class="filter-popover-stars">' + starsHtml + "</div>" +
    "</div>" +
    '<div class="filter-popover-section">' +
    '<label class="filter-popover-toggle">' +
    '<input type="checkbox" id="filter-popover-fav"' + (state.fav ? " checked" : "") + "> Nur Favoriten" +
    "</label>" +
    "</div>" +
    genreSectionHtml +
    '<button type="button" class="filter-popover-reset" id="filter-popover-reset">Zur\u00fccksetzen</button>'
  );
}
export interface FilterChipView {
  html: string;
  active: boolean;
  title: string;
}
/** "Filtern" button label (updateFilterChips). Icon passed in (IC_FILTER). */
export function filterCombinedChipView(state: FilterPopoverState, icFilter: string): FilterChipView {
  const activeCount = (state.rating > 0 ? 1 : 0) + (state.fav ? 1 : 0) + (state.genre ? 1 : 0);
  return {
    html: icFilter + " Filtern" + (activeCount ? " (" + activeCount + ")" : ""),
    active: activeCount > 0,
    title: activeCount
      ? activeCount + " Filter aktiv \u2014 klicken zum Anpassen"
      : "Filtern (Bewertung, Favoriten, Genre)",
  };
}
/**
 * "Ausgeblendet" button view, or null when threshold <= 0 (button hidden).
 * Counts items rated 1..threshold-1; "(N/M)" always shown (stable width).
 */
export function filterHiddenChipView(
  items: Array<{ rating?: number | null }>,
  threshold: number,
  showHidden: boolean,
  icEye: string
): FilterChipView | null {
  if (!(threshold > 0)) return null;
  const hidden = items.filter((t) => {
    const r = t.rating || 0;
    return r > 0 && r < threshold;
  }).length;
  return {
    html: icEye + " Ausgeblendet (" + hidden + "/" + items.length + ")",
    active: !showHidden,
    title: showHidden
      ? "Ausgeblendete Songs sichtbar \u2014 klicken zum Verstecken"
      : "Ausgeblendete Songs einblenden",
  };
}