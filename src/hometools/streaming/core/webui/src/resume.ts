/**
 * Auto-resume target picking. Ported from `player_js/_folder_browse.py::
 * _restoreLastEpisode` (pure half). DOM (markActive/scroll), fetch and toast
 * stay legacy.
 */
export interface ResumeHit {
  idx: number;
  pos: number;
  label: string;
}

interface Titled {
  relative_path: string;
  title?: string;
}

function indexByPath(items: Titled[]): Record<string, number> {
  const m: Record<string, number> = Object.create(null);
  items.forEach((it, i) => {
    m[it.relative_path] = i;
  });
  return m;
}

/** localStorage snapshot hit: path present in `items` and nothing selected yet. */
export function findResumeLocal(
  items: Titled[],
  local: { path?: string; position_seconds?: number } | null | undefined,
  currentIndex: number
): ResumeHit | null {
  if (!local || !local.path || currentIndex >= 0) return null;
  const idx = indexByPath(items)[local.path];
  if (idx === undefined) return null;
  return { idx, pos: Number(local.position_seconds || 0), label: (items[idx] && items[idx].title) || local.path };
}

/** First server "recent" entry in `items` with position >= 5s. */
export function findResumeRecent(
  items: Titled[],
  entries: { relative_path?: string; position_seconds?: number }[] | null | undefined,
  currentIndex: number
): ResumeHit | null {
  if (!entries || !entries.length || currentIndex >= 0) return null;
  const byPath = indexByPath(items);
  for (const e of entries) {
    const rp = e.relative_path || "";
    const idx = byPath[rp];
    if (idx === undefined) continue;
    const pos = Number(e.position_seconds || 0);
    if (pos < 5) continue;
    return { idx, pos, label: (items[idx] && items[idx].title) || rp };
  }
  return null;
}

