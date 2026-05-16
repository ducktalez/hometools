"""HTML skeleton builder — ``render_media_page`` is the single page template."""

from __future__ import annotations

import html

from ._css import render_base_css
from ._player_js import render_player_js
from ._pwa import render_pwa_head_tags
from ._svg import (
    SVG_BACK,
    SVG_CLOSE_X,
    SVG_EXPAND,
    SVG_FULLSCREEN,
    SVG_HISTORY,
    SVG_LYRICS,
    SVG_MENU,
    SVG_NEXT,
    SVG_PAUSE,  # noqa: F401 — kept for completeness / future use
    SVG_PIP,
    SVG_PLAY,
    SVG_PREV,
    SVG_QUEUE,
    SVG_REFRESH,
    SVG_REPEAT,
    SVG_SHUFFLE,
)


def render_media_page(
    *,
    title: str,
    emoji: str,
    items_json: str,
    media_element_tag: str,
    extra_css: str = "",
    api_path: str,
    item_noun: str = "track",
    theme_color: str = "#1db954",
    player_bar_style: str = "classic",
    safe_mode: bool = False,
    enable_shuffle: bool = False,
    enable_repeat: bool = False,
    enable_rating_write: bool = False,
    enable_metadata_edit: bool = False,
    enable_recent: bool = True,
    enable_lyrics: bool = False,
    enable_playlists: bool = False,
    playlist_sync_interval_ms: int = 30000,
    min_rating: int = 0,
    enable_auto_resume: bool = True,
    crossfade_duration: int = 0,
    debug_filter: bool = False,
    language_groups_json: str = "{}",
    default_language: str = "de",
) -> str:
    """Build the complete HTML page for a media streaming UI.

    The page starts in folder-grid view.  Clicking a folder shows the
    track list with the player.  A back button returns to the grid.
    *media_element_tag* should be ``audio`` or ``video``.

    *player_bar_style* selects the bottom player layout:
    ``classic``  — single-row with inline range slider (default).
    ``waveform`` — two-row layout with audio waveform / video thumbnails.

    *enable_rating_write* adds clickable rating stars to the player bar
    and wires up the ``POST /api/<media>/rating`` endpoint (audio only).

    *enable_metadata_edit* adds a pencil edit button per track that opens
    an inline modal for editing title / artist / album tags (audio only).
    Wires up to ``POST /api/<media>/metadata/edit``.
    """
    css = render_base_css() + extra_css
    js = render_player_js(
        api_path=api_path,
        item_noun=item_noun,
        file_emoji=emoji,
        player_bar_style=player_bar_style,
        enable_offline=not safe_mode,
        enable_shuffle=enable_shuffle,
        enable_repeat=enable_repeat,
        enable_rating_write=enable_rating_write,
        enable_metadata_edit=enable_metadata_edit,
        enable_recent=enable_recent,
        enable_lyrics=enable_lyrics,
        enable_playlists=enable_playlists,
        playlist_sync_interval_ms=playlist_sync_interval_ms,
        min_rating=min_rating,
        enable_auto_resume=enable_auto_resume,
        crossfade_duration=crossfade_duration,
        debug_filter=debug_filter,
        language_groups_json=language_groups_json,
        default_language=default_language,
    )
    is_video = media_element_tag == "video"
    pwa_tags = "" if safe_mode else render_pwa_head_tags(theme_color=theme_color, standalone=not is_video)
    shuffle_btn_html = (
        f'<button class="ctrl-btn shuffle-btn" id="btn-shuffle" title="Shuffle">{SVG_SHUFFLE}</button>' if enable_shuffle else ""
    )
    repeat_btn_html = (
        f'<button class="ctrl-btn repeat-btn" id="btn-repeat" title="Wiederholen">{SVG_REPEAT}</button>' if enable_repeat else ""
    )
    queue_btn_html = f'<button class="ctrl-btn queue-btn" id="btn-queue" title="Warteschlange">{SVG_QUEUE}<span class="queue-badge" id="queue-badge"></span></button>'
    sw_register = (
        ""
        if safe_mode
        else """
  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(function(){});
    }
  </script>"""
    )
    mode_controls_html = (
        '<span class="downloaded-pill is-offline" id="downloaded-pill">Safe Mode</span>'
        '<span class="tools-pill" id="tools-pill" title="Tools &amp; Einstellungen">Tools'
        '<button class="tools-pill-refresh" id="tools-pill-refresh" title="Katalog neu laden" hidden>' + SVG_REFRESH + "</button></span>"
        if safe_mode
        else '<span class="tools-pill" id="tools-pill" title="Tools &amp; Einstellungen">Tools'
        '<button class="tools-pill-refresh" id="tools-pill-refresh" title="Katalog neu laden" hidden>' + SVG_REFRESH + "</button></span>"
    )
    tools_panel_html = f"""
  <div class="tools-panel-backdrop" id="tools-panel-backdrop" hidden>
    <div class="tools-panel">
      <div class="tools-panel-header">
        <div class="tools-panel-title">Tools &amp; Einstellungen</div>
        <a class="audit-btn" id="audit-btn" href="/audit" title="\u00c4nderungsverlauf">{SVG_HISTORY}</a>
      </div>
      <button class="tools-activate-all" id="tools-activate-all" title="Tool-Modus mit den konfigurierten Einstellungen aktivieren">Tool-Modus aktivieren</button>

      <div class="tools-section-heading">Titelbearbeitung</div>
      <div class="tools-item">
        <div>
          <div class="tools-item-label">Inline-Ratings</div>
          <div class="tools-item-desc">Bewertungssterne direkt in der Track-Liste anzeigen</div>
        </div>
        <label class="tools-toggle">
          <input type="checkbox" id="tool-inline-ratings">
          <span class="tools-toggle-track"></span>
        </label>
      </div>
      <div class="tools-item">
        <div>
          <div class="tools-item-label">Dateien verschieben</div>
          <div class="tools-item-desc">Songs in andere Ordner verschieben (2x2 Schnellwahl + Dropdown)</div>
        </div>
        <label class="tools-toggle">
          <input type="checkbox" id="tool-file-mover">
          <span class="tools-toggle-track"></span>
        </label>
      </div>

      <div class="tools-section-heading">Bibliothek</div>
      <div class="tools-item">
        <div>
          <div class="tools-item-label">Downloads</div>
          <div class="tools-item-desc">Download-Buttons pro Track anzeigen</div>
        </div>
        <label class="tools-toggle">
          <input type="checkbox" id="tool-downloads" checked>
          <span class="tools-toggle-track"></span>
        </label>
      </div>
      <div class="tools-item">
        <div>
          <div class="tools-item-label">Zur Playlist hinzuf&uuml;gen</div>
          <div class="tools-item-desc">Playlist-Buttons pro Track anzeigen</div>
        </div>
        <label class="tools-toggle">
          <input type="checkbox" id="tool-playlists" checked>
          <span class="tools-toggle-track"></span>
        </label>
      </div>
      <div class="tools-item">
        <div>
          <div class="tools-item-label">Duplikate suchen</div>
          <div class="tools-item-desc">Doppelte Dateien in der Bibliothek finden</div>
          <button class="dupe-show-link" id="dupe-show-link"></button>
        </div>
        <label class="tools-toggle">
          <input type="checkbox" id="tool-duplicates">
          <span class="tools-toggle-track"></span>
        </label>
      </div>

      <div class="tools-section-heading">Ansicht</div>
      <div class="tools-item tools-item--full">
        <div class="tools-item-label">Ordnerdaten erneuern</div>
        <div class="tools-item-desc">Position des Buttons &bdquo;Katalog neu laden&ldquo;</div>
        <div class="tools-buttongroup" id="tool-refresh-position" role="group">
          <button type="button" class="tools-buttongroup-btn" data-value="header">Kopfleiste</button>
          <button type="button" class="tools-buttongroup-btn" data-value="tools-pill">Im Tools-Button</button>
          <button type="button" class="tools-buttongroup-btn" data-value="off">Aus</button>
        </div>
      </div>

      <button class="tools-panel-close" id="tools-panel-close">Schlie&szlig;en</button>
    </div>
  </div>
  <div class="dupe-panel-backdrop" id="dupe-panel-backdrop" hidden>
    <div class="dupe-panel">
      <div class="dupe-panel-title">Duplikate</div>
      <div class="dupe-panel-subtitle" id="dupe-panel-subtitle"></div>
      <div id="dupe-panel-body"></div>
      <button class="dupe-panel-play-all" id="dupe-panel-play-all">Alle Duplikate abspielen</button>
      <button class="dupe-panel-close" id="dupe-panel-close">Schließen</button>
    </div>
  </div>"""
    offline_library_html = (
        ""
        if safe_mode
        else """
  <div class="offline-library" id="offline-library" hidden>
    <div class="offline-panel">
      <div class="offline-head">
        <div class="offline-title-wrap">
          <div class="offline-title">Offline-Bibliothek</div>
          <div class="offline-subtitle">Gespeicherte Downloads verwalten und direkt offline abspielen</div>
        </div>
        <button class="offline-close" id="offline-close" title="Schließen">Schließen</button>
      </div>
      <div class="offline-summary" id="offline-storage-summary">Noch keine Offline-Downloads.</div>
      <div class="offline-summary-detail" id="offline-storage-detail"></div>
      <div class="offline-toolbar">
        <select id="offline-sort">
          <option value="newest">Neueste zuerst</option>
          <option value="oldest">Älteste zuerst</option>
          <option value="title">Titel A–Z</option>
          <option value="size">Größte zuerst</option>
        </select>
        <button class="offline-action-btn" id="offline-persist-btn" type="button">Speicher persistent halten</button>
        <button class="offline-action-btn" id="offline-prune-btn" type="button">Alte Downloads aufräumen</button>
      </div>
      <ul class="offline-download-list" id="offline-download-list"></ul>
    </div>
  </div>"""
    )

    edit_modal_html = (
        ""
        if not enable_metadata_edit
        else """
  <!-- metadata edit modal -->
  <div class="edit-modal-backdrop" id="edit-modal-backdrop" hidden>
    <div class="edit-modal" role="dialog" aria-modal="true" aria-labelledby="edit-modal-heading">
      <div class="edit-modal-heading" id="edit-modal-heading">Metadaten bearbeiten</div>
      <div class="edit-field">
        <label for="edit-modal-title-input">Titel</label>
        <input id="edit-modal-title-input" type="text" autocomplete="off" />
      </div>
      <div class="edit-field">
        <label for="edit-modal-artist-input">Interpret</label>
        <input id="edit-modal-artist-input" type="text" autocomplete="off" />
      </div>
      <div class="edit-field">
        <label for="edit-modal-album-input">Album <span style="color:var(--sub);font-size:0.75rem">(optional)</span></label>
        <input id="edit-modal-album-input" type="text" autocomplete="off" />
      </div>
      <div class="edit-field" id="edit-modal-rating-field">
        <label>Bewertung</label>
        <div class="edit-modal-rating" id="edit-modal-rating"></div>
      </div>
      <input type="hidden" id="edit-modal-path" />
      <input type="hidden" id="edit-modal-idx" />
      <div class="edit-modal-actions">
        <button class="edit-modal-cancel" id="edit-modal-cancel-btn">Abbrechen</button>
        <button class="edit-modal-save" id="edit-modal-save-btn">Speichern</button>
      </div>
    </div>
  </div>"""
    )

    playlist_pill_html = ""  # Pill entfernt — Playlists als Pseudo-Ordner unter Downloaded

    playlist_library_html = ""  # Library-Panel entfernt — Playlists als Pseudo-Ordner

    playlist_modal_html = (
        ""
        if not enable_playlists or safe_mode
        else """
  <div class="playlist-modal-backdrop" id="playlist-modal-backdrop" hidden>
    <div class="playlist-modal" role="dialog" aria-modal="true">
      <div class="playlist-modal-heading">Zur Playlist hinzuf\u00fcgen</div>
      <ul class="playlist-modal-list" id="playlist-modal-list"></ul>
      <div class="playlist-modal-new">
        <input id="playlist-modal-new-name" type="text" placeholder="Neue Playlist\u2026" autocomplete="off" />
        <button id="playlist-modal-new-btn">Erstellen</button>
      </div>
      <div class="playlist-modal-close"><button id="playlist-modal-close-btn">Abbrechen</button></div>
    </div>
  </div>"""
    )

    recent_section_html = (
        """  <div class="recent-section" id="recent-section" hidden>
    <div class="recent-section-title">Zuletzt gespielt</div>
    <div class="recent-scroll"></div>
  </div>"""
        if enable_recent
        else ""
    )

    lyrics_btn_html = (
        f'<button class="ctrl-btn lyrics-btn" id="btn-lyrics" title="Songtext anzeigen">{SVG_LYRICS}</button>' if enable_lyrics else ""
    )
    lyrics_panel_html = (
        """  <div class="lyrics-panel" id="lyrics-panel">
    <div class="lyrics-panel-head">
      <span class="lyrics-panel-title">Songtext</span>
      <button class="lyrics-close-btn" id="lyrics-close-btn" title="Schlie\u00dfen">\u00d7</button>
    </div>
    <div class="lyrics-body" id="lyrics-body">
      <div class="lyrics-loading">Lade Songtext\u2026</div>
    </div>
  </div>"""
        if enable_lyrics
        else ""
    )

    queue_panel_html = """  <div class="queue-panel" id="queue-panel">
    <div class="queue-drag-handle" id="queue-drag-handle"><div class="queue-drag-handle-bar"></div></div>
    <div class="queue-panel-head">
      <span class="queue-panel-title">Warteschlange</span>
      <div style="display:flex;align-items:center;gap:0.5rem">
        <button class="queue-close-btn" id="queue-clear-btn" title="Alle entfernen" style="font-size:0.72rem;display:none">Leeren</button>
        <button class="queue-close-btn" id="queue-close-btn" title="Schlie\u00dfen">\u00d7</button>
      </div>
    </div>
    <div class="queue-body" id="queue-body">
      <div class="queue-empty">Die Warteschlange ist leer.</div>
    </div>
  </div>"""

    if player_bar_style == "waveform":
        player_bar_html = f"""
  <div class="player-bar waveform view-hidden">
    <div class="player-bar-top">
      <img class="track-thumb" id="player-thumb" src="" alt="" style="display:none">
      <div class="player-info">
        <div class="player-title"  id="player-title">No {item_noun} selected</div>
        <div class="player-artist" id="player-artist">&ndash;</div>
        <div class="player-rating" id="player-rating" hidden></div>
      </div>
      <div class="player-controls">
        <button class="ctrl-btn"            id="btn-prev" title="Previous">{SVG_PREV}</button>
        <button class="ctrl-btn play-pause" id="btn-play" title="Play / Pause">{SVG_PLAY}</button>
        <button class="ctrl-btn"            id="btn-next" title="Next">{SVG_NEXT}</button>
        <button class="ctrl-btn pip-btn"    id="btn-pip"  title="Bild-in-Bild" hidden>{SVG_PIP}</button>
        {lyrics_btn_html}
        {shuffle_btn_html}
        {repeat_btn_html}
        {queue_btn_html}
      </div>
    </div>
    <div class="progress-wrap">
      <span class="time-label"     id="time-cur">0:00</span>
      <div class="progress-track" id="progress-track">
        <canvas id="waveform-canvas"></canvas>
        <input type="range" id="progress-bar" min="0" step="0.1" value="0" />
        <div class="thumb-preview" id="thumb-preview">
          <canvas id="thumb-canvas" width="160" height="90"></canvas>
          <span class="thumb-time" id="thumb-time"></span>
        </div>
      </div>
      <span class="time-label end" id="time-dur">0:00</span>
    </div>
  </div>"""
    else:
        player_bar_html = f"""
  <div class="player-bar classic view-hidden">
    <img class="track-thumb" id="player-thumb" src="" alt="" style="display:none">
    <div class="player-info">
      <div class="player-title"  id="player-title">No {item_noun} selected</div>
      <div class="player-artist" id="player-artist">&ndash;</div>
      <div class="player-rating" id="player-rating" hidden></div>
    </div>
    <div class="player-controls">
      <button class="ctrl-btn"            id="btn-prev" title="Previous">{SVG_PREV}</button>
      <button class="ctrl-btn play-pause" id="btn-play" title="Play / Pause">{SVG_PLAY}</button>
      <button class="ctrl-btn"            id="btn-next" title="Next">{SVG_NEXT}</button>
      <button class="ctrl-btn pip-btn"    id="btn-pip"  title="Bild-in-Bild" hidden>{SVG_PIP}</button>
      {lyrics_btn_html}
      {shuffle_btn_html}
      {repeat_btn_html}
      {queue_btn_html}
    </div>
    <div class="progress-wrap">
      <span class="time-label"     id="time-cur">0:00</span>
      <div class="progress-track" id="progress-track">
        <canvas id="waveform-canvas" class="waveform-canvas"></canvas>
        <input type="range" id="progress-bar" min="0" step="0.1" value="0" />
        <div class="thumb-preview" id="thumb-preview">
          <canvas id="thumb-canvas" width="160" height="90"></canvas>
          <span class="thumb-time" id="thumb-time"></span>
        </div>
      </div>
      <span class="time-label end" id="time-dur">0:00</span>
    </div>
  </div>"""

    # Build the player section: video mode → overlay modal, audio mode → inline bar
    if is_video:
        player_section_html = f"""  <!-- Video overlay (replaces bottom player bar in video mode) -->
  <div class="video-overlay view-hidden" id="video-overlay">
    <div class="video-overlay-header">
      <button class="video-overlay-close" id="video-close-btn" title="Zur\u00fcck zur Liste">{SVG_BACK}</button>
      <span class="video-overlay-title-text" id="video-overlay-title-text"></span>
      <button class="video-fs-btn" id="video-fs-btn" title="Vollbild">{SVG_FULLSCREEN}</button>
    </div>
    <div class="video-wrap">
      <video id="player" preload="auto" playsinline autopictureinpicture></video>
    </div>
{player_bar_html}
  </div>
  <!-- Floating mini-player (when exiting overlay via Escape / fullscreenchange) -->
  <div class="video-float-container" id="video-float-container">
    <div id="video-float-wrap" style="width:100%;height:100%"></div>
    <div class="video-float-controls">
      <button class="video-float-btn" id="float-expand-btn" title="Zur\u00fcck zum Video">{SVG_EXPAND}</button>
      <button class="video-float-btn" id="float-close-btn" title="Schlie\u00dfen">{SVG_CLOSE_X}</button>
    </div>
  </div>
  <!-- Video mini bar (compact strip when overlay is closed but video active) -->
  <div class="video-mini-bar" id="video-mini-bar" hidden>
    <img class="track-thumb" id="mini-thumb" src="" alt="" style="display:none">
    <div class="mini-info">
      <div class="mini-title" id="mini-title"></div>
      <div class="mini-artist" id="mini-artist"></div>
    </div>
    <button class="mini-btn mini-expand-btn" id="mini-expand-btn" title="Video \u00f6ffnen">{SVG_EXPAND}</button>
    <button class="mini-btn mini-play-btn" id="mini-play-btn">{SVG_PLAY}</button>
  </div>"""
    else:
        player_section_html = f"""  <audio id="player" preload="auto" playsinline></audio>
{player_bar_html}"""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{html.escape(title)}</title>
{pwa_tags}
  <style>{css}</style>
</head>
<body>
  <header>
    <button class="back-btn" id="back-btn" title="Back to folders">{SVG_BACK}</button>
    <button class="logo-home-btn" id="header-logo" title="Zurück zur Startseite">{emoji}</button>
    <span class="logo-title" id="header-title"></span>
    <button class="play-all-btn" id="play-all-btn" title="Play all">{SVG_PLAY} Play All</button>
    <button class="view-toggle" id="view-toggle" title="Ansicht wechseln">{SVG_MENU}</button>
    <button class="refresh-btn" id="refresh-btn" title="Katalog neu laden">{SVG_REFRESH}</button>
    {mode_controls_html}
    {playlist_pill_html}
    <input id="global-search-input" class="header-search view-hidden" type="search" autocomplete="off" />
  </header>

  <!-- breadcrumb navigation -->
  <nav class="breadcrumb" id="breadcrumb"></nav>

  <!-- folder filter bar (kept for test compatibility, always hidden) -->
  <div class="folder-filter-bar" id="folder-filter-bar" hidden></div>

  <!-- recently played (root view only, hidden until JS populates) -->
  {recent_section_html}

  <!-- folder grid (default view) -->
  <div class="folder-grid" id="folder-grid"></div>

  <!-- filter bar (visible inside a folder) -->
  <div class="filter-bar view-hidden">
    <div class="search-wrap">
      <input id="search-input" type="search" placeholder="Suche\u2026" autocomplete="off" />
      <span class="track-count" id="track-count"></span>
    </div>
    <select id="sort-field">
      <option value="custom">Liste &#x21C5;</option>
      <option value="title">Title &#x21C5;</option>
      <option value="artist">Artist &#x21C5;</option>
      <option value="path">Path &#x21C5;</option>
      <option value="recent">Neueste &#x21C5;</option>
    </select>
    <button class="filter-chip" id="filter-rating" title="Nach Bewertung filtern"></button>
    <button class="filter-chip" id="filter-fav" title="Nur Favoriten anzeigen"></button>
    <button class="filter-chip" id="filter-genre" title="Nach Genre filtern"></button>
    <button class="filter-chip" id="filter-hidden" title="Ausgeblendete Songs anzeigen" style="display:none"></button>
  </div>

  <!-- track list (visible inside a folder) -->
  <div class="track-list-wrap view-hidden" id="track-view">
    <ul class="track-list" id="track-list"></ul>
  </div>

{offline_library_html}
{tools_panel_html}
{edit_modal_html}
{lyrics_panel_html}
{queue_panel_html}
{playlist_library_html}
{playlist_modal_html}

{player_section_html}

  <script id="initial-data" type="application/json">{items_json}</script>
  <script>{js}</script>
{sw_register}
</body>
</html>
"""
