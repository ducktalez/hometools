/**
 * Playlist load + cross-device sync polling — ported from
 * `player_js/_playlists.py` (loadUserPlaylists, _startPlaylistSync,
 * _stopPlaylistSync, _onPlaylistVisibility, _pollPlaylistVersion,
 * _snapshotPlaylists, _restorePlaylists).
 *
 * State: `_userPlaylists`/`_playlistRevision` are shared with other legacy
 * fragments -> accessed via `htState` (userPlaylists/playlistRevision).
 * The sync timer was private to these functions -> moved in as module state.
 * CFG-derived values + the "re-render root" callback come in as `opts`.
 */

import { getState } from "./stateBridge";

export interface PlaylistSyncOptions {
  enabled: boolean;
  apiPath: string;
  versionPath: string;
  intervalMs: number;
  /** Called after a remote revision bump reloaded the playlists. */
  onRemoteUpdate?: () => void;
}

let _timer: ReturnType<typeof setInterval> | null = null;
let _opts: PlaylistSyncOptions | null = null;

/** Fetch all playlists into htState. Resolves to the list ([] on failure). */
export function loadUserPlaylists(opts: PlaylistSyncOptions): Promise<unknown[]> {
  const st = getState();
  if (!opts.enabled || !st) return Promise.resolve([]);
  return fetch(opts.apiPath)
    .then((r) => r.json())
    .then((d) => {
      st.userPlaylists = d.items || [];
      if (typeof d.revision === "number") st.playlistRevision = d.revision;
      return st.userPlaylists;
    })
    .catch(() => []);
}

function pollVersion(): void {
  const st = getState();
  const o = _opts;
  if (!st || !o) return;
  fetch(o.versionPath)
    .then((r) => r.json())
    .then((d) => {
      if (typeof d.revision === "number" && d.revision > st.playlistRevision) {
        loadUserPlaylists(o).then(() => {
          if (o.onRemoteUpdate) o.onRemoteUpdate();
        });
      }
    })
    .catch(() => {
      /* offline — ignore */
    });
}

function onVisibility(): void {
  stopTimer();
  if (document.hidden || !_opts) return;
  pollVersion(); // resume: immediate check, then interval
  _timer = setInterval(pollVersion, _opts.intervalMs);
}

function stopTimer(): void {
  if (_timer) {
    clearInterval(_timer);
    _timer = null;
  }
}

/** Start polling (idempotent). Pauses while the tab is hidden. */
export function startPlaylistSync(opts: PlaylistSyncOptions): void {
  if (!opts.enabled) return;
  stopPlaylistSync();
  _opts = opts;
  _timer = setInterval(pollVersion, opts.intervalMs);
  document.addEventListener("visibilitychange", onVisibility);
}

/** Stop polling and detach the visibility listener. */
export function stopPlaylistSync(): void {
  stopTimer();
  document.removeEventListener("visibilitychange", onVisibility);
}

/** Deep copy of the current playlists (for optimistic-UI rollback). */
export function snapshotPlaylists(): unknown[] {
  const st = getState();
  return st ? JSON.parse(JSON.stringify(st.userPlaylists)) : [];
}

export function restorePlaylists(snap: unknown[]): void {
  const st = getState();
  if (st) st.userPlaylists = snap;
}

