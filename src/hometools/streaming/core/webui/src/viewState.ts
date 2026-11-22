/**
 * Persistence stays with the writers (popover / toolbar / view toggles).
 *
 * (always undefined there), so video could start in table mode.
 */

export type FolderViewMode = "list" | "grid";
export type TrackViewMode = "rows" | "table";

export interface ViewState {
  filterRating: number;
  filterFav: boolean;
  filterGenre: string;
  /** true = hidden items shown greyed out instead of removed. */
  showHidden: boolean;
  viewMode: FolderViewMode;
  trackViewMode: TrackViewMode;
}

function read(storage: Pick<Storage, "getItem">, key: string): string | null {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

/** Build initial state from localStorage. `isVideoMode` forbids table view. */
export function initViewState(isVideoMode: boolean, storage: Pick<Storage, "getItem"> = localStorage): ViewState {
  const vm = read(storage, "ht-view-mode");
  const tvm = read(storage, "ht-track-view-mode");
  return {
    filterRating: parseInt(read(storage, "ht-filter-rating") || "0", 10) || 0,
    filterFav: read(storage, "ht-filter-fav") === "1",
    filterGenre: read(storage, "ht-filter-genre") || "",
    showHidden: read(storage, "ht-show-hidden") !== "0",
    viewMode: vm === "list" || vm === "grid" ? vm : "list",
    trackViewMode: tvm === "table" && !isVideoMode ? "table" : "rows",
  };
}
