"""Tasks / board HTML rendering for the /board page.

The board surfaces open library tasks — primarily **missing individual
episodes** within series seasons, plus secondary structure hints from the
library scan.  It is a standalone dark-theme page (same family as /audit)
that fetches ``GET /api/<media>/board``.
"""

from __future__ import annotations

import html

_BOARD_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
:root { --bg:#121212; --surface:#1e1e1e; --surface2:#2a2a2a; --accent:#bb86fc;
        --text:#e0e0e0; --sub:#999; --danger:#cf6679; --warn:#ffd700; }
body { background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       font-size:14px; min-height:100vh; }
header { display:flex; align-items:center; gap:1rem; padding:0.75rem 1.2rem;
         background:var(--surface); border-bottom:1px solid #333; flex-wrap:wrap; }
header h1 { font-size:1rem; font-weight:600; flex:1; display:flex; align-items:center; gap:0.4rem; }
header h1 svg { width:18px; height:18px; }
header a.back { color:var(--sub); font-size:0.82rem; text-decoration:none; }
header a.back:hover { color:var(--text); }
button.reload { background:var(--accent); color:#000; border:none; border-radius:6px;
  padding:0.35rem 0.9rem; cursor:pointer; font-weight:600; font-size:0.82rem; }
button.reload:hover { background:#d1a3ff; }
main { padding:1rem 1.2rem; max-width:980px; margin:0 auto; }
.section-title { font-size:0.78rem; text-transform:uppercase; letter-spacing:.07em;
  color:var(--sub); margin:1.4rem 0 0.6rem; display:flex; align-items:center; gap:0.5rem; }
.section-title .badge { background:var(--surface2); color:var(--text); border-radius:10px;
  padding:1px 8px; font-size:0.72rem; letter-spacing:0; }
.empty { text-align:center; color:var(--sub); padding:2rem 1rem; font-size:0.9rem; }
.card { background:var(--surface); border:1px solid #2c2c2c; border-radius:10px;
  padding:0.7rem 0.9rem; margin-bottom:0.6rem; }
.card-head { display:flex; align-items:baseline; gap:0.5rem; flex-wrap:wrap; }
.card-series { font-weight:600; font-size:0.95rem; }
.card-season { font-size:0.78rem; color:var(--sub); }
.card-folder { font-size:0.72rem; color:var(--sub); font-family:monospace;
  margin-top:0.15rem; word-break:break-all; }
.eps { margin-top:0.5rem; display:flex; gap:0.35rem; flex-wrap:wrap; align-items:center; }
.eps-label { font-size:0.72rem; color:var(--sub); margin-right:0.2rem; }
.ep-missing { background:rgba(207,102,121,0.18); color:var(--danger); border:1px solid var(--danger);
  border-radius:6px; padding:1px 7px; font-size:0.76rem; font-weight:600; font-variant-numeric:tabular-nums; }
.ep-range { font-size:0.72rem; color:var(--sub); margin-left:0.3rem; }
.issue { background:var(--surface); border:1px solid #2c2c2c; border-left:3px solid var(--warn);
  border-radius:8px; padding:0.6rem 0.8rem; margin-bottom:0.5rem; }
.issue.info { border-left-color:#4a90d9; }
.issue-head { display:flex; gap:0.5rem; align-items:baseline; flex-wrap:wrap; }
.issue-check { font-size:0.7rem; font-family:monospace; background:var(--surface2);
  padding:1px 6px; border-radius:4px; color:var(--sub); }
.issue-folder { font-weight:600; font-size:0.85rem; word-break:break-all; }
.issue-msg { font-size:0.82rem; margin-top:0.3rem; }
.issue-hint { font-size:0.74rem; color:var(--sub); margin-top:0.25rem; }
.toast { position:fixed; bottom:1.5rem; right:1.5rem; background:var(--surface);
         border:1px solid #444; border-radius:8px; padding:0.7rem 1rem; font-size:0.82rem;
         box-shadow:0 4px 20px #0008; opacity:0; transform:translateY(10px);
         transition:all 0.25s; pointer-events:none; z-index:999; }
.toast.show { opacity:1; transform:translateY(0); }
"""

_BOARD_JS = """
function showToast(msg, duration) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(function() { t.classList.remove('show'); }, duration || 2800);
}

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function fmtEp(n) { return 'E' + (n < 10 ? '0' + n : n); }

function renderMissing(gaps) {
  var host = document.getElementById('missing-list');
  var badge = document.getElementById('missing-count');
  if (!host) return;
  var total = 0;
  gaps.forEach(function(g) { total += (g.missing_count || (g.missing_episodes || []).length); });
  if (badge) badge.textContent = total + ' fehlend';
  if (!gaps.length) {
    host.innerHTML = '<div class="empty">Keine fehlenden Einzelfolgen gefunden. \\u2713</div>';
    return;
  }
  host.innerHTML = gaps.map(function(g) {
    var eps = (g.missing_episodes || []).map(function(n) {
      return '<span class="ep-missing">' + fmtEp(n) + '</span>';
    }).join('');
    var seasonStr = 'Staffel ' + g.season;
    var range = 'vorhanden E' + g.first_episode + '\\u2013E' + g.last_episode +
      ' (' + (g.present_episodes || []).length + ')';
    return '<div class="card">'
      + '<div class="card-head">'
      + '<span class="card-series">' + esc(g.series) + '</span>'
      + '<span class="card-season">' + esc(seasonStr) + '</span>'
      + '</div>'
      + (g.folder ? '<div class="card-folder">' + esc(g.folder) + '</div>' : '')
      + '<div class="eps"><span class="eps-label">Fehlt:</span>' + eps
      + '<span class="ep-range">' + esc(range) + '</span></div>'
      + '</div>';
  }).join('');
}

function renderIssues(issues) {
  var host = document.getElementById('issues-list');
  var badge = document.getElementById('issues-count');
  if (!host) return;
  if (badge) badge.textContent = issues.length + '';
  if (!issues.length) {
    host.innerHTML = '<div class="empty">Keine weiteren Hinweise.</div>';
    return;
  }
  host.innerHTML = issues.map(function(i) {
    return '<div class="issue ' + (i.severity === 'info' ? 'info' : '') + '">'
      + '<div class="issue-head">'
      + '<span class="issue-check">' + esc(i.check) + '</span>'
      + '<span class="issue-folder">' + esc(i.folder) + '</span>'
      + '</div>'
      + '<div class="issue-msg">' + esc(i.message) + '</div>'
      + (i.hint ? '<div class="issue-hint">\\u2192 ' + esc(i.hint) + '</div>' : '')
      + '</div>';
  }).join('');
}

function load() {
  var mHost = document.getElementById('missing-list');
  if (mHost) mHost.innerHTML = '<div class="empty">Lade\\u2026</div>';
  fetch('/api/' + MEDIA_TYPE + '/board')
    .then(function(r) {
      if (!r.ok) return Promise.reject(new Error('HTTP ' + r.status));
      return r.json();
    })
    .then(function(d) {
      renderMissing((d && d.missing_episodes) || []);
      renderIssues((d && d.issues) || []);
    })
    .catch(function(err) {
      var msg = err && err.message ? err.message : '';
      showToast('Fehler beim Laden des Boards' + (msg ? ' (' + msg + ')' : ''));
      var host = document.getElementById('missing-list');
      if (host) host.innerHTML = '<div class="empty">Board konnte nicht geladen werden. '
        + '<button class="reload" onclick="load()">Erneut versuchen</button></div>';
    });
}

document.getElementById('reload-btn')?.addEventListener('click', load);
load();
"""


def render_board_page_html(*, server: str, media_type: str, title: str) -> str:
    """Return the standalone tasks/board HTML page.

    *server*     — display label, e.g. ``"hometools video"``
    *media_type* — ``"audio"`` or ``"video"`` (used in JS for API calls)
    *title*      — ``<title>`` text
    """
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{_BOARD_CSS}</style>
</head>
<body>
  <header>
    <h1><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/><polyline points="9,14 11,16 15,11"/></svg>Aufgaben-Board — {html.escape(server)}</h1>
    <button class="reload" id="reload-btn" type="button">Aktualisieren</button>
    <a class="back" href="/">\u2190 Zur\u00fcck zur App</a>
  </header>
  <main>
    <div class="section-title">Fehlende Folgen <span class="badge" id="missing-count">\u2026</span></div>
    <div id="missing-list"><div class="empty">Lade\u2026</div></div>

    <div class="section-title">Bibliotheks-Hinweise <span class="badge" id="issues-count">\u2026</span></div>
    <div id="issues-list"><div class="empty">Lade\u2026</div></div>
  </main>
  <div id="toast" class="toast"></div>
  <script>var MEDIA_TYPE = '{media_type}';</script>
  <script>{_BOARD_JS}</script>
</body>
</html>"""
