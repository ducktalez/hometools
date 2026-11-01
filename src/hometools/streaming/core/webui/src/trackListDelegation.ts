/**
 * Track-list event delegation — ported from `player_js/_search_filter.py`
 * (_wireTrackListDelegation). Handler refs are module-private; re-wiring
 * (called once per renderTracks) removes the previous listeners first.
 * `filteredItems`/`userQueue` via `htState`; every action via `TrackListHooks`.
 *
 * Behaviour fix vs. legacy: the dblclick listener was an anonymous function
 * and piled up on every re-wire (playTrack fired N times). Now named + removed.
 */

import { getState } from "./stateBridge";
import { wasDrag } from "./clickGuard";
import { queueIndexOf } from "./queue";

export interface TrackListHooks {
  metadataEditEnabled: boolean;
  playlistsEnabled: boolean;
  itemNoun: string;
  setInlineRating(index: number, stars: number): void;
  openBpmAdjustMenu(index: number, btn: HTMLElement): void;
  deleteTrackDownload(url: string, btn: HTMLElement): void;
  cancelDownload(url: string, btn: HTMLElement): void;
  downloadTrack(url: string, title: string | undefined, btn: HTMLElement, meta: Record<string, string>): void;
  toggleFavorite(item: LegacyMediaItem, btn: HTMLElement): void;
  openEditModal(index: number): void;
  /** `loadUserPlaylists().then(() => openPlaylistModal(rp))` */
  openPlaylistModalFor(relativePath: string): void;
  removeFromQueue(index: number): void;
  addToQueue(item: LegacyMediaItem): void;
  showToast(msg: string): void;
  moveFileToFolder(index: number, target: string): void;
  deleteTrackFromList(index: number): void;
  openTrackCtxMenu(btn: HTMLElement, relativePath: string | undefined, title: string | undefined): void;
  revealInExplorer(relativePath: string | undefined, title: string | undefined): void;
  playTrack(index: number): void;
  selectTrackRow(index: number): void;
  saveInlineTableEdit(editable: HTMLElement): void;
}

const ROW_SEL = ".track-item:not(.missing-episode):not(.debug-filtered)";
const EDITABLE_SEL = '.track-title-text[contenteditable="true"], .track-artist[contenteditable="true"]';

let _click: ((e: Event) => void) | null = null;
let _change: ((e: Event) => void) | null = null;
let _focusout: ((e: Event) => void) | null = null;
let _keydown: ((e: Event) => void) | null = null;
let _dblclick: ((e: Event) => void) | null = null;
let _wiredList: HTMLElement | null = null;

function unwire(): void {
  const tl = _wiredList;
  if (!tl) return;
  if (_click) tl.removeEventListener("click", _click);
  if (_change) tl.removeEventListener("change", _change);
  if (_focusout) tl.removeEventListener("focusout", _focusout);
  if (_keydown) tl.removeEventListener("keydown", _keydown);
  if (_dblclick) tl.removeEventListener("dblclick", _dblclick);
  _click = _change = _focusout = _keydown = _dblclick = null;
  _wiredList = null;
}

export function wireTrackListDelegation(trackList: HTMLElement, h: TrackListHooks): void {
  unwire();
  _wiredList = trackList;

  _click = (ev: Event): void => {
    const e = ev as MouseEvent;
    const target = e.target as Element;
    const stop = (): void => {
      e.stopPropagation();
      e.preventDefault();
    };
    const st = getState();
    const items = st ? st.filteredItems : [];

    const ratingStar = target.closest<HTMLElement>(".track-inline-rating-star");
    if (ratingStar) {
      stop();
      const idx = Number(ratingStar.dataset.index);
      const t = items[idx];
      const cur = Math.round((t && (t.rating as number)) || 0);
      const clicked = Number(ratingStar.dataset.star);
      h.setInlineRating(idx, clicked === cur ? 0 : clicked);
      return;
    }
    const bpmPillBtn = target.closest<HTMLElement>('.meta-pill[data-action="calc-bpm"]');
    if (bpmPillBtn) {
      stop();
      h.openBpmAdjustMenu(Number(bpmPillBtn.dataset.index), bpmPillBtn);
      return;
    }
    const dlBtn = target.closest<HTMLElement>(".track-dl-btn");
    if (dlBtn) {
      stop();
      const url = dlBtn.dataset.streamUrl || "";
      const meta = {
        artist: dlBtn.dataset.artist || "",
        relativePath: dlBtn.dataset.relativePath || "",
        thumbnailUrl: dlBtn.dataset.thumbnailUrl || "",
        mediaType: dlBtn.dataset.mediaType || h.itemNoun,
      };
      if (dlBtn.classList.contains("cached")) h.deleteTrackDownload(url, dlBtn);
      else if (dlBtn.classList.contains("downloading")) h.cancelDownload(url, dlBtn);
      else h.downloadTrack(url, dlBtn.dataset.title, dlBtn, meta);
      return;
    }
    const pinBtn = target.closest<HTMLElement>(".track-pin-btn");
    if (pinBtn) {
      stop();
      const pinItem = items.find((it) => it.relative_path === pinBtn.dataset.relativePath);
      if (pinItem) h.toggleFavorite(pinItem, pinBtn);
      return;
    }
    if (h.metadataEditEnabled) {
      const editBtn = target.closest<HTMLElement>(".track-edit-btn");
      if (editBtn) {
        stop();
        h.openEditModal(Number(editBtn.dataset.index));
        return;
      }
    }
    if (h.playlistsEnabled) {
      const plBtn = target.closest<HTMLElement>(".track-playlist-btn");
      if (plBtn) {
        stop();
        h.openPlaylistModalFor(plBtn.dataset.relativePath || "");
        return;
      }
    }
    const queueBtn = target.closest<HTMLElement>(".track-queue-btn");
    if (queueBtn) {
      stop();
      const qi = queueIndexOf(st ? st.userQueue : [], queueBtn.dataset.relativePath || "");
      if (qi >= 0) {
        h.removeFromQueue(qi);
        h.showToast("Aus Warteschlange entfernt");
      } else {
        const qidx = Number(queueBtn.dataset.index);
        if (qidx >= 0 && qidx < items.length) h.addToQueue(items[qidx]);
      }
      return;
    }
    const movQuick = target.closest<HTMLElement>(".move-quick-btn");
    if (movQuick) {
      stop();
      h.moveFileToFolder(Number(movQuick.dataset.index), movQuick.dataset.target || "");
      return;
    }
    const trashBtn = target.closest<HTMLElement>(".track-delete-btn, .move-delete-btn");
    if (trashBtn) {
      stop();
      h.deleteTrackFromList(Number(trashBtn.dataset.index));
      return;
    }
    const kebabBtn = target.closest<HTMLElement>(".track-kebab-btn");
    if (kebabBtn) {
      stop();
      h.openTrackCtxMenu(kebabBtn, kebabBtn.dataset.relativePath, kebabBtn.dataset.title);
      return;
    }
    const revealBtn = target.closest<HTMLElement>(".track-reveal-btn");
    if (revealBtn) {
      stop();
      h.revealInExplorer(revealBtn.dataset.relativePath, revealBtn.dataset.title);
      return;
    }
    const playBtn = target.closest<HTMLElement>(".track-play-btn");
    if (playBtn) {
      stop();
      h.playTrack(Number(playBtn.dataset.index));
      return;
    }
    // Caret placement in inline-editable cells must not select/play the row.
    if (target.closest('[contenteditable="true"]')) return;
    // Row click: hover devices only select; touch devices play directly.
    const trackItem = target.closest<HTMLElement>(ROW_SEL);
    if (trackItem && !wasDrag(e) && !window.getSelection()?.toString()) {
      const idx = Number(trackItem.dataset.index);
      if (window.matchMedia && window.matchMedia("(hover: hover)").matches) h.selectTrackRow(idx);
      else h.playTrack(idx);
    }
  };

  _change = (ev: Event): void => {
    const movSel = (ev.target as Element).closest<HTMLSelectElement>(".move-folder-select");
    if (!movSel) return;
    ev.stopPropagation();
    const target = movSel.value;
    if (!target) return;
    h.moveFileToFolder(Number(movSel.dataset.index), target);
    movSel.value = "";
  };

  _focusout = (ev: Event): void => {
    const editable = (ev.target as Element).closest<HTMLElement>(EDITABLE_SEL);
    if (editable) h.saveInlineTableEdit(editable);
  };

  _keydown = (ev: Event): void => {
    const e = ev as KeyboardEvent;
    const editable = (e.target as Element).closest<HTMLElement>(EDITABLE_SEL);
    if (!editable) return;
    if (e.key === "Enter") {
      e.preventDefault();
      editable.blur();
    } else if (e.key === "Escape") {
      e.preventDefault();
      editable.dataset.cancelled = "1";
      editable.blur();
    }
  };

  _dblclick = (ev: Event): void => {
    const target = ev.target as Element;
    if (target.closest('[contenteditable="true"]')) return;
    const row = target.closest<HTMLElement>(ROW_SEL);
    if (row) h.playTrack(Number(row.dataset.index));
  };

  trackList.addEventListener("click", _click);
  trackList.addEventListener("change", _change);
  trackList.addEventListener("focusout", _focusout);
  trackList.addEventListener("keydown", _keydown);
  trackList.addEventListener("dblclick", _dblclick);
}

/** Detach all delegated listeners (tests / view teardown). */
export function unwireTrackListDelegation(): void {
  unwire();
}

