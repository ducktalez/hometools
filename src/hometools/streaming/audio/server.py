"""Minimal local web server for the audio streaming prototype."""

from __future__ import annotations

import html
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from hometools.config import get_audio_library_dir
from hometools.constants import AUDIO_SUFFIX
from hometools.streaming.audio.catalog import (
    AudioTrack,
    build_audio_index,
    list_artists,
    query_tracks,
)


HTML_PAGE_TITLE = "hometools audio prototype"


def resolve_audio_path(library_dir: Path, encoded_relative_path: str) -> Path:
    """Resolve and validate a requested track path inside the library root."""
    root = library_dir.resolve()
    relative_path = Path(unquote(encoded_relative_path))
    candidate = (root / relative_path).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Requested path escapes the configured audio library.") from exc

    if not candidate.is_file():
        raise FileNotFoundError(f"Audio file not found: {relative_path}")
    if candidate.suffix.lower() not in AUDIO_SUFFIX:
        raise ValueError(f"Unsupported audio suffix for streaming: {candidate.suffix}")

    return candidate


def render_audio_index_html(tracks: list[AudioTrack], library_dir: Path) -> str:
    """Render a tiny browser-based audio player UI."""
    artists = list_artists(tracks)
    artist_options = "\n".join(
        f'<option value="{html.escape(artist, quote=True)}">{html.escape(artist)}</option>'
        for artist in artists
    )

    items = "\n".join(
        (
            "<li>"
            f"<button class=\"track-button\" data-stream=\"{html.escape(track.stream_url, quote=True)}\" "
            f"data-label=\"{html.escape(f'{track.artist} - {track.title}', quote=True)}\">"
            f"{html.escape(track.artist)} - {html.escape(track.title)}"
            "</button>"
            f"<div class=\"track-path\">{html.escape(track.relative_path)}</div>"
            "</li>"
        )
        for track in tracks
    )

    if not items:
        items = "<li>No audio files found yet. Run a manual sync first.</li>"

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{HTML_PAGE_TITLE}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem auto; max-width: 900px; padding: 0 1rem; }}
    h1, p {{ margin-bottom: 0.8rem; }}
    audio {{ width: 100%; margin: 1rem 0 1.5rem; }}
    .controls {{ display: grid; grid-template-columns: 1.7fr 1fr 1fr; gap: 0.6rem; margin-bottom: 1rem; }}
    input, select {{ padding: 0.5rem; border: 1px solid #ccc; border-radius: 6px; }}
    ul {{ list-style: none; padding: 0; }}
    li {{ border-bottom: 1px solid #ddd; padding: 0.75rem 0; }}
    .track-button {{ background: #1f6feb; color: white; border: 0; border-radius: 6px; padding: 0.55rem 0.8rem; cursor: pointer; }}
    .track-path {{ color: #666; font-size: 0.9rem; margin-top: 0.35rem; word-break: break-all; }}
    .hint {{ color: #555; }}
  </style>
</head>
<body>
  <h1>hometools audio prototype</h1>
  <p class=\"hint\">Library: <code>{html.escape(str(library_dir))}</code></p>
  <p class=\"hint\">This MVP streams only local files that were copied into the configured audio library.</p>
  <div class=\"controls\">
    <input id=\"search-input\" type=\"search\" placeholder=\"Search artist, title or path\" />
    <select id=\"artist-filter\">
      <option value=\"all\">All artists</option>
      {artist_options}
    </select>
    <select id=\"sort-field\">
      <option value=\"artist\">Sort: artist</option>
      <option value=\"title\">Sort: title</option>
      <option value=\"path\">Sort: path</option>
    </select>
  </div>
  <audio id=\"player\" controls preload=\"none\"></audio>
  <p id=\"current-track\" class=\"hint\">No track selected.</p>
  <ul id=\"track-list\">{items}</ul>
  <script>
    const player = document.getElementById('player');
    const currentTrack = document.getElementById('current-track');
    const searchInput = document.getElementById('search-input');
    const artistFilter = document.getElementById('artist-filter');
    const sortField = document.getElementById('sort-field');
    const trackList = document.getElementById('track-list');

    function wireTrackButtons() {{
      for (const button of document.querySelectorAll('.track-button')) {{
        button.addEventListener('click', () => {{
          player.src = button.dataset.stream;
          player.play();
          currentTrack.textContent = `Playing: ${'{'}button.dataset.label{'}'}`;
        }});
      }}
    }}

    function renderTracks(tracks) {{
      if (!tracks.length) {{
        trackList.innerHTML = '<li>No matching tracks found.</li>';
        return;
      }}
      trackList.innerHTML = tracks.map((track) => (
        '<li>' +
          `<button class="track-button" data-stream="${'{'}track.stream_url{'}'}" data-label="${'{'}track.artist{'}'} - ${'{'}track.title{'}'}">` +
          `${'{'}track.artist{'}'} - ${'{'}track.title{'}'}` +
          '</button>' +
          `<div class="track-path">${'{'}track.relative_path{'}'}</div>` +
        '</li>'
      )).join('');
      wireTrackButtons();
    }}

    async function fetchTracks() {{
      const params = new URLSearchParams({{
        q: searchInput.value,
        artist: artistFilter.value,
        sort: sortField.value,
      }});
      const response = await fetch(`/api/audio/tracks?${'{'}params.toString(){'}'}`);
      if (!response.ok) {{
        trackList.innerHTML = '<li>Could not load tracks.</li>';
        return;
      }}
      const payload = await response.json();
      renderTracks(payload.tracks || []);
    }}

    wireTrackButtons();
    searchInput.addEventListener('input', fetchTracks);
    artistFilter.addEventListener('change', fetchTracks);
    sortField.addEventListener('change', fetchTracks);
  </script>
</body>
</html>
"""


def create_app(library_dir: Path | None = None) -> Any:
    """Create the FastAPI application for local audio streaming."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    resolved_library_dir = (library_dir or get_audio_library_dir()).expanduser()
    app = FastAPI(title="hometools audio streaming prototype")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "library_dir": str(resolved_library_dir),
        }

    @app.get("/", response_class=HTMLResponse)
    def audio_home() -> HTMLResponse:
        tracks = build_audio_index(resolved_library_dir)
        return HTMLResponse(render_audio_index_html(tracks, resolved_library_dir))

    @app.get("/api/audio/tracks")
    def audio_tracks(q: str | None = None, artist: str | None = None, sort: str = "artist") -> dict[str, object]:
        tracks = build_audio_index(resolved_library_dir)
        filtered_tracks = query_tracks(tracks, q=q, artist=artist, sort_by=sort)
        return {
            "library_dir": str(resolved_library_dir),
            "count": len(filtered_tracks),
            "tracks": [track.to_dict() for track in filtered_tracks],
            "artists": list_artists(tracks),
            "query": {
                "q": q or "",
                "artist": artist or "all",
                "sort": sort,
            },
        }

    @app.get("/audio/stream")
    def audio_stream(path: str) -> FileResponse:
        try:
            file_path = resolve_audio_path(resolved_library_dir, path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        return FileResponse(file_path, media_type=media_type, filename=file_path.name)

    return app



