/** Runtime config rendered by the server into the `#ht-config` JSON blob
 * (`server_utils/_html.py::_render_player_config_json`). */
export interface PlayerConfig {
  itemNoun: string;
  fileEmoji: string;
  apiPath: string;
  enableOffline: boolean;
  enableShuffle: boolean;
  enableRepeat: boolean;
  enableSkipIntro: boolean;
  enableRatingWrite: boolean;
  minRating: number;
  debugFilter: boolean;
  enableRecent: boolean;
  enableAutoResume: boolean;
  crossfadeDuration: number;
  enableMetadataEdit: boolean;
  enableLyrics: boolean;
  enablePlaylists: boolean;
  playlistSyncIntervalMs: number;
  languageGroups: Record<string, string>;
  defaultLanguage: string;
  audiobookDirs: string[];
  bpmMin: number;
  bpmMax: number;
  /** Markup of the server-side `_svg.py` constants, keyed without the `SVG_` prefix. */
  icons: Record<string, string>;
}

/** Parse `#ht-config`; `{}`-like defaults when the tag is missing or invalid. */
export function readConfig(): PlayerConfig {
  const el = document.getElementById("ht-config");
  try {
    return JSON.parse((el && el.textContent) || "{}") as PlayerConfig;
  } catch {
    return {} as PlayerConfig;
  }
}
