/** Insert placeholder rows for missing episodes between two present
 * episodes of the same season. Ported from player_js/_search_filter.py.
 * Pure — no window reads. Bridged onto window by main.ts. */

export interface EpisodeGapPlaceholder {
  _missing: true;
  season: number;
  episode: number;
}

export function withMissingEpisodes<T extends { season?: number; episode?: number }>(
  tracks: T[]
): (T | EpisodeGapPlaceholder)[] {
  const result: (T | EpisodeGapPlaceholder)[] = [];
  for (let i = 0; i < tracks.length; i++) {
    const t = tracks[i];
    if (i > 0) {
      const prev = tracks[i - 1];
      const sameSeason = (prev.season || 0) > 0 && (prev.season || 0) === (t.season || 0);
      if (sameSeason && (prev.episode || 0) > 0 && (t.episode || 0) > 0) {
        const gap = (t.episode || 0) - (prev.episode || 0);
        for (let g = 1; g < gap && g < 20; g++) {
          result.push({ _missing: true, season: prev.season as number, episode: (prev.episode || 0) + g });
        }
      }
    }
    result.push(t);
  }
  return result;
}

