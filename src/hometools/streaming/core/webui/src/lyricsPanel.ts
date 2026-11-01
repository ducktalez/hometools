/**
 * Lyrics side panel. Ported from `player_js/_core.py` (open/close/render,
 * cache, button wiring). State is private to this module (cache + open
 * flag + DOM refs) — only `isOpen()` is read by the legacy script, so it
 * moved along (same pattern as `clickGuard.ts`).
 */

export interface LyricsCfg {
  enabled: boolean;
  apiPath: string;
  escHtml: (s: unknown) => string;
  /** Currently playing track (legacy reads filteredItems/playlistItems). */
  getCurrentTrack: () => { relative_path: string; title?: string } | null | undefined;
}

export interface LyricsPanel {
  open(relativePath: string, trackTitle?: string): void;
  close(): void;
  isOpen(): boolean;
}

export function lyricsBodyHtml(text: string, trackTitle: string | undefined, esc: (s: unknown) => string): string {
  return text
    ? '<div class="lyrics-text">' + esc(text) + "</div>"
    : '<div class="lyrics-empty">Kein Songtext f\u00fcr \u201e' + esc(trackTitle || "diesen Titel") + "\u201c hinterlegt.</div>";
}

export function initLyricsPanel(cfg: LyricsCfg): LyricsPanel {
  const btn = document.getElementById("btn-lyrics");
  const panel = document.getElementById("lyrics-panel");
  const body = document.getElementById("lyrics-body");
  const closeBtn = document.getElementById("lyrics-close-btn");
  const cache: Record<string, string> = {};
  let isOpenFlag = false;

  function render(text: string, trackTitle?: string): void {
    if (!body) return;
    body.innerHTML = lyricsBodyHtml(text, trackTitle, cfg.escHtml);
    if (btn) btn.classList.toggle("has-lyrics", !!text);
  }

  function open(relativePath: string, trackTitle?: string): void {
    if (!cfg.enabled || !panel) return;
    isOpenFlag = true;
    panel.classList.add("visible");
    if (btn) btn.title = "Songtext schlie\u00dfen";
    if (relativePath in cache) {
      render(cache[relativePath], trackTitle);
      return;
    }
    if (body) body.innerHTML = '<div class="lyrics-loading">Lade Songtext\u2026</div>';
    fetch(cfg.apiPath + "?path=" + encodeURIComponent(relativePath), { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const text = d && d.lyrics ? String(d.lyrics) : "";
        cache[relativePath] = text;
        if (isOpenFlag) render(text, trackTitle);
      })
      .catch(() => {
        if (body) body.innerHTML = '<div class="lyrics-empty">Songtext konnte nicht geladen werden.</div>';
      });
  }

  function close(): void {
    isOpenFlag = false;
    if (panel) panel.classList.remove("visible");
    if (btn) btn.title = "Songtext anzeigen";
  }

  if (btn) {
    btn.addEventListener("click", () => {
      if (isOpenFlag) {
        close();
      } else {
        const t = cfg.getCurrentTrack();
        if (t) open(t.relative_path, t.title);
      }
    });
  }
  if (closeBtn) closeBtn.addEventListener("click", close);

  return { open, close, isOpen: () => isOpenFlag };
}

