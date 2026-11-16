/**
 * Delegated click handler on the folder grid for the dynamically rendered
 * tools-row cards (refresh catalog / add / remove extra folder). Ported from
 * `player_js/_queue.py`. Installed once at startup; the grid element lives
 * for the whole page, so no cleanup is needed.
 */

export interface FolderGridEventOpts {
  folderGrid: HTMLElement | null;
  refreshCatalog(): void;
  addExtraFolder(): void;
  removeExtraFolder(): void;
}

/** Map a click target to the tools-row action it hits, if any. */
export function folderGridAction(target: Element | null): "refresh" | "add" | "remove" | null {
  if (!target || typeof target.closest !== "function") return null;
  if (target.closest(".refresh-catalog-card")) return "refresh";
  if (target.closest("#add-folder-card")) return "add";
  if (target.closest("#remove-folder-card")) return "remove";
  return null;
}

export function initFolderGridEvents(o: FolderGridEventOpts): void {
  const grid = o.folderGrid;
  if (!grid) return;
  grid.addEventListener("click", (e: Event) => {
    const a = folderGridAction(e.target as Element | null);
    if (a === "refresh") o.refreshCatalog();
    else if (a === "add") o.addExtraFolder();
    else if (a === "remove") o.removeExtraFolder();
  });
}

