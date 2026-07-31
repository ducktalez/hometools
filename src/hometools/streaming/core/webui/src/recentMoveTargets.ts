/** File-mover MRU folder list (localStorage). Ported from
 * `player_js/_library_tools.py` — self-contained, no shared-state deps. */

const KEY = "ht-move-recent";

export function getRecentMoveTargets(): string[] {
  try {
    return (JSON.parse(localStorage.getItem(KEY) || "[]") as string[]).slice(0, 4);
  } catch {
    return [];
  }
}

export function saveRecentMoveTarget(folder: string): void {
  const recent = getRecentMoveTargets().filter((f) => f !== folder);
  recent.unshift(folder);
  try {
    localStorage.setItem(KEY, JSON.stringify(recent.slice(0, 4)));
  } catch {
    /* ignore quota/private-mode errors */
  }
}

