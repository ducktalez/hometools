"""CSS fragment: root (split from the former monolithic _css.py)."""

from __future__ import annotations


def render_root_css() -> str:
    """Return the root section of the dark-theme CSS."""
    return """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #121212; --surface: #1e1e1e; --surface2: #282828;
  --accent: #1db954; --text: #fff; --sub: #b3b3b3;
  --header-h: 56px; --filter-h: 52px; --player-h: 80px;
  --sat: env(safe-area-inset-top, 0px);
  --sab: env(safe-area-inset-bottom, 0px);
  --sal: env(safe-area-inset-left, 0px);
  --sar: env(safe-area-inset-right, 0px);
}
body {
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  height: 100dvh; display: flex; flex-direction: column; overflow: hidden;
}

/* ── Header ── */
header {
  height: calc(var(--header-h) + var(--sat));
  padding-top: var(--sat);
  background: var(--surface);
  display: flex; align-items: center; padding-left: max(1rem, var(--sal)); padding-right: max(1rem, var(--sar)); gap: 0.75rem;
  flex-shrink: 0; border-bottom: 1px solid #333;
}
.logo { font-size: 1.1rem; font-weight: 700; color: var(--accent); user-select: none; }
.logo-home-btn {
  background: none; border: none; line-height: 1;
  cursor: pointer; padding: 0 2px; color: inherit; flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
  display: inline-flex; align-items: center; justify-content: center;
}
.logo-home-btn svg { width: 20px; height: 20px; }
.logo-home-btn:hover { opacity: 0.75; }
.logo-home-btn:disabled, .logo-home-btn.disabled { opacity: 0.4; cursor: not-allowed; pointer-events: none; }
.back-btn:disabled, .back-btn.disabled { opacity: 0.4; cursor: not-allowed; pointer-events: none; }
.play-all-btn:disabled, .play-all-btn.disabled { opacity: 0.4; cursor: not-allowed; pointer-events: none; }
.logo-title {
  font-size: 1.1rem; font-weight: 700; color: var(--accent);
  user-select: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1 1 auto; min-width: 0;
}
/* Flexible spacer — pushes play-all/view-toggle/tools/search to the right,
   keeping the header structure constant regardless of which leading
   elements (logo-title vs. breadcrumb) are currently visible. */
.header-spacer { flex: 1 1 auto; min-width: 0.5rem; }
.offline-close, .offline-action-btn {
  background: var(--surface2); color: var(--text); border: 1px solid #444;
  border-radius: 999px; cursor: pointer; padding: 0.4rem 0.8rem;
  font-size: 0.8rem; -webkit-tap-highlight-color: transparent;
}
.offline-close:hover, .offline-action-btn:hover {
  color: var(--accent); border-color: var(--accent);
}
.downloaded-pill {
  font-size: 0.72rem; color: var(--sub); border: 1px solid #3a3a3a;
  border-radius: 999px; padding: 0.28rem 0.55rem; margin-left: 0.45rem;
  cursor: pointer; -webkit-tap-highlight-color: transparent;
  transition: color 0.15s, border-color 0.15s;
}
.downloaded-pill:hover, .downloaded-pill.has-downloads { color: var(--accent); border-color: var(--accent); }
.downloaded-pill.is-offline { color: #ffcc00; border-color: #ffcc00; }
"""
