"""Audit / Control-Panel HTML rendering for the /audit page."""

from __future__ import annotations

import html

_AUDIT_PANEL_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
:root { --bg:#121212; --surface:#1e1e1e; --surface2:#2a2a2a; --accent:#1db954;
        --text:#e0e0e0; --sub:#999; --danger:#cf6679; --warn:#ffd700; }
body { background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       font-size:14px; min-height:100vh; }
header { display:flex; align-items:center; gap:1rem; padding:0.75rem 1.2rem;
         background:var(--surface); border-bottom:1px solid #333; flex-wrap:wrap; }
header h1 { font-size:1rem; font-weight:600; flex:1; }
.filter-bar { display:flex; gap:0.5rem; flex-wrap:wrap; padding:0.75rem 1.2rem; background:var(--surface2); border-bottom:1px solid #333; }
.filter-bar input, .filter-bar select { background:var(--bg); color:var(--text); border:1px solid #444;
  border-radius:6px; padding:0.35rem 0.6rem; font-size:0.82rem; flex:1; min-width:140px; }
.filter-bar input:focus, .filter-bar select:focus { outline:none; border-color:var(--accent); }
.filter-bar button { background:var(--accent); color:#000; border:none; border-radius:6px;
  padding:0.35rem 0.9rem; cursor:pointer; font-weight:600; font-size:0.82rem; white-space:nowrap; }
.filter-bar button:hover { background:#1ed760; }
.empty { text-align:center; color:var(--sub); padding:3rem 1rem; font-size:0.9rem; }
table { width:100%; border-collapse:collapse; }
thead th { text-align:left; padding:0.5rem 0.75rem; font-size:0.75rem; text-transform:uppercase;
           letter-spacing:.06em; color:var(--sub); border-bottom:1px solid #333; white-space:nowrap; }
tbody tr { border-bottom:1px solid #262626; transition:background 0.1s; }
tbody tr:hover { background:var(--surface2); }
tbody tr.undone { opacity:0.45; }
td { padding:0.5rem 0.75rem; vertical-align:middle; }
.td-time { font-size:0.72rem; color:var(--sub); white-space:nowrap; }
.td-action { font-size:0.72rem; font-family:monospace; background:var(--surface2);
             padding:1px 5px; border-radius:4px; white-space:nowrap; }
.td-path { font-size:0.78rem; max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.td-path a { color:var(--accent); text-decoration:none; }
.td-path a:hover { text-decoration:underline; }
.td-change { font-size:0.82rem; white-space:nowrap; }
.old-val { color:var(--sub); text-decoration:line-through; }
.arrow { color:var(--sub); margin:0 0.25rem; }
.new-val { color:var(--accent); font-weight:600; }
.td-undo { white-space:nowrap; }
.undo-btn { background:none; border:1px solid #555; color:var(--text); border-radius:5px;
            padding:0.2rem 0.55rem; cursor:pointer; font-size:0.75rem; transition:all 0.12s; }
.undo-btn:hover { border-color:var(--warn); color:var(--warn); }
.undo-btn:disabled { opacity:0.35; cursor:default; }
.undo-btn.done { border-color:#555; color:var(--sub); }
.badge-undone { font-size:0.7rem; color:var(--sub); font-style:italic; }
.stars { display:inline-flex; align-items:center; gap:1px; color:var(--warn); vertical-align:middle; }
.audit-star { display:inline-flex; width:14px; height:14px; color:#555; flex-shrink:0; }
.audit-star svg { width:14px; height:14px; }
.audit-star.active { color:var(--warn); }
.star-value { font-size:0.72rem; color:var(--sub); margin-left:2px; }
.rating-hist-link { font-size:0.7rem; color:var(--sub); margin-left:0.4rem; text-decoration:none; display:inline-flex; align-items:center; vertical-align:middle; }
.rating-hist-link svg { width:13px; height:13px; }
.rating-hist-link:hover { color:var(--accent); }
.toast { position:fixed; bottom:1.5rem; right:1.5rem; background:var(--surface);
         border:1px solid #444; border-radius:8px; padding:0.7rem 1rem; font-size:0.82rem;
         box-shadow:0 4px 20px #0008; opacity:0; transform:translateY(10px);
         transition:all 0.25s; pointer-events:none; z-index:999; }
.toast.show { opacity:1; transform:translateY(0); pointer-events:auto; }
"""

_AUDIT_PANEL_JS = """
var SERVER_LABEL = document.querySelector('header h1')?.textContent || '';
var IC_STAR_FILLED = '<svg viewBox="0 0 24 24"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="currentColor"/></svg>';
var IC_STAR_EMPTY  = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/></svg>';
var IC_CLIPBOARD = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/></svg>';

function fmtDate(iso) {
  try {
    var d = new Date(iso);
    return d.toLocaleDateString('de-DE', {day:'2-digit',month:'2-digit',year:'numeric'})
      + ' ' + d.toLocaleTimeString('de-DE', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
  } catch(e) { return iso; }
}

function fmtStars(v) {
  if (v == null || v === '') return '–';
  var n = parseFloat(v);
  if (isNaN(n)) return String(v);
  var full = Math.round(n);
  var html = '';
  for (var i = 1; i <= 5; i++) {
    html += '<span class="audit-star' + (i <= full ? ' active' : '') + '">' +
      (i <= full ? IC_STAR_FILLED : IC_STAR_EMPTY) + '</span>';
  }
  return html + ' <span class="star-value">(' + n.toFixed(1) + ')</span>';
}

function fmtValue(field, v) {
  if (field === 'rating') return '<span class="stars">' + fmtStars(v) + '</span>';
  return v == null ? '–' : String(v);
}

function showToast(msg, duration) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(function() { t.classList.remove('show'); }, duration || 2800);
}

var _entries = [];

function renderTable(entries) {
  _entries = entries;
  var tbody = document.querySelector('#log-table tbody');
  if (!tbody) return;
  if (!entries.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty">Noch keine Einträge.</td></tr>';
    return;
  }
  tbody.innerHTML = entries.map(function(e) {
    var undone = !!e.undone;
    var filename = e.path ? e.path.split('/').pop() : '–';
    var shortPath = e.path || '–';
    var histLink = '<a class="rating-hist-link" href="?path_filter=' + encodeURIComponent(e.path) + '" title="Nur dieses File anzeigen">' + IC_CLIPBOARD + '</a>';
    var changeHtml = fmtValue(e.field, e.old_value)
      + '<span class="arrow">→</span>'
      + fmtValue(e.field, e.new_value);
    var undoHtml = undone
      ? '<span class="badge-undone">Rückgängig ' + fmtDate(e.undone_at) + '</span>'
      : '<button class="undo-btn" data-id="' + e.entry_id + '" onclick="doUndo(this)">Rückgängig</button>';
    return '<tr class="' + (undone ? 'undone' : '') + '">'
      + '<td class="td-time">' + fmtDate(e.timestamp) + '</td>'
      + '<td class="td-action">' + (e.action || '–') + '</td>'
      + '<td class="td-path" title="' + shortPath + '">' + filename + histLink + '</td>'
      + '<td class="td-change">' + changeHtml + '</td>'
      + '<td class="td-undo">' + undoHtml + '</td>'
      + '</tr>';
  }).join('');
}

function loadEntries() {
  var path = document.getElementById('f-path')?.value || '';
  var action = document.getElementById('f-action')?.value || '';
  var url = '/api/' + MEDIA_TYPE + '/audit?limit=500';
  if (path) url += '&path_filter=' + encodeURIComponent(path);
  if (action) url += '&action_filter=' + encodeURIComponent(action);
  fetch(url)
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(d) { if (d) renderTable(d.items || []); })
    .catch(function() { showToast('Fehler beim Laden der Einträge'); });
}

function doUndo(btn) {
  var entryId = btn.dataset.id;
  if (!entryId) return;
  btn.disabled = true;
  btn.textContent = '…';
  fetch('/api/' + MEDIA_TYPE + '/audit/undo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entry_id: entryId })
  })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        showToast('Rückgängig gemacht ✓');
        loadEntries();
      } else {
        showToast('Fehler: ' + (d.detail || 'Unbekannt'));
        btn.disabled = false;
        btn.textContent = 'Rückgängig';
      }
    })
    .catch(function() {
      showToast('Netzwerkfehler');
      btn.disabled = false;
      btn.textContent = 'Rückgängig';
    });
}

/* Pre-fill filters from URL params */
var _params = new URLSearchParams(window.location.search);
if (_params.get('path_filter')) document.getElementById('f-path').value = _params.get('path_filter');

document.getElementById('f-form')?.addEventListener('submit', function(e) {
  e.preventDefault();
  loadEntries();
});
document.getElementById('f-clear')?.addEventListener('click', function() {
  document.getElementById('f-path').value = '';
  document.getElementById('f-action').value = '';
  history.replaceState(null, '', window.location.pathname);
  loadEntries();
});

loadEntries();
"""


def render_audit_panel_html(*, server: str, media_type: str, title: str) -> str:
    """Return the standalone audit / control-panel HTML page.

    *server*     — display label, e.g. ``"hometools audio"``
    *media_type* — ``"audio"`` or ``"video"`` (used in JS for API calls)
    *title*      — ``<title>`` text
    """
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{_AUDIT_PANEL_CSS}</style>
</head>
<body>
  <header>
    <h1><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px;vertical-align:text-bottom;margin-right:4px"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10,9 9,9 8,9"/></svg>Audit-Log — {html.escape(server)}</h1>
    <a href="/" style="color:var(--sub);font-size:0.82rem;text-decoration:none;">← Zurück zur App</a>
  </header>
  <div class="filter-bar">
    <form id="f-form" style="display:contents">
      <input id="f-path" type="text" placeholder="Datei-Filter (Teilstring)…">
      <select id="f-action">
        <option value="">Alle Aktionen</option>
        <option value="rating_write">rating_write</option>
        <option value="tag_write">tag_write</option>
        <option value="file_rename">file_rename</option>
      </select>
      <button type="submit">Filter anwenden</button>
      <button id="f-clear" type="button" style="background:var(--surface2);border:1px solid #555;color:var(--text);">Zurücksetzen</button>
    </form>
  </div>
  <table id="log-table">
    <thead>
      <tr>
        <th>Zeitpunkt</th>
        <th>Aktion</th>
        <th>Datei</th>
        <th>Änderung</th>
        <th>Rückgängig</th>
      </tr>
    </thead>
    <tbody>
      <tr><td colspan="5" class="empty">Lade…</td></tr>
    </tbody>
  </table>
  <div id="toast" class="toast"></div>
  <script>var MEDIA_TYPE = '{media_type}';</script>
  <script>{_AUDIT_PANEL_JS}</script>
</body>
</html>"""
