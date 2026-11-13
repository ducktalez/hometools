/**
 * Queue (Warteschlange) controller: owns panel DOM lookup, open flag, user
 * height, wiring (close/clear/resize/peek/DnD) and badge/button sync.
 * Replaces the queue state/wrappers formerly in `player_js/_core.py` and
 * `_queue.py`. DOM nodes are looked up lazily (never stale).
 */

import { addToQueue, removeFromQueue, clearQueueAction, playFromQueue, queueMove } from "./queue";
import { initQueueDragDrop, destroyQueueDragDrop } from "./queueDragDrop";
import {
  renderQueuePanel,
  syncQueueBottom,
  initQueueResize,
  initQueuePeekHandle,
  openQueuePanel,
  closeQueuePanel,
  toggleQueuePanel,
  updateQueueBadge,
  updateQueueButtons,
} from "./queuePanelUi";
import { getState } from "./stateBridge";

export const QUEUE_HEIGHT_KEY = "hometools_queue_height";
export const QUEUE_MIN_H = 220; // head ~57px + >= 3 items

export interface QueueControllerCfg {
  itemNoun: string;
  filePlaceholder: string;
  icRemove: string;
  esc(s: unknown): string;
  toast(msg: string): void;
  playItem(item: LegacyMediaItem, index: number): void;
  lyricsOpen(): boolean;
  closeLyrics(): void;
}

export interface QueueController {
  add(item: LegacyMediaItem | null | undefined): void;
  remove(index: number): void;
  clear(): void;
  playFrom(index: number): void;
  open(): void;
  close(): void;
  toggle(): void;
  isOpen(): boolean;
  updateBadge(): void;
  updateButtons(): void;
  render(): void;
}

function el(id: string): HTMLElement | null {
  return document.getElementById(id);
}

function loadUserHeight(): number | null {
  try {
    const sh = localStorage.getItem(QUEUE_HEIGHT_KEY);
    if (sh) {
      const v = parseInt(sh, 10);
      return v >= QUEUE_MIN_H ? v : null;
    }
  } catch {
    /* private mode */
  }
  return null;
}

export function initQueueController(cfg: QueueControllerCfg): QueueController {
  let isOpenFlag = false;
  let userHeight: number | null = loadUserHeight();

  const queue = (): LegacyMediaItem[] => {
    const s = getState();
    return s ? s.userQueue : [];
  };

  const updateBadge = (): void => updateQueueBadge(el("queue-peek-badge"), el("queue-peek-handle"), queue().length);
  const updateButtons = (): void => updateQueueButtons(queue());
  const sync = (): void => syncQueueBottom(el("queue-panel"), userHeight, QUEUE_MIN_H);
  const render = (): void =>
    renderQueuePanel({
      body: el("queue-body"),
      clearBtn: el("queue-clear-btn"),
      queue: queue(),
      esc: cfg.esc,
      filePlaceholder: cfg.filePlaceholder,
      icRemove: cfg.icRemove,
      playFromQueue: (i) => ctl.playFrom(i),
      removeFromQueue: (i) => ctl.remove(i),
      initDnd: () => initQueueDragDrop({ move: (f, t) => queueMove(f, t), render }),
    });
  const onChanged = (): void => {
    updateBadge();
    updateButtons();
    if (isOpenFlag) render();
  };
  const panelHooks = {
    ensureDom: () => {},
    getPanel: () => el("queue-panel"),
    getPeekHandle: () => el("queue-peek-handle"),
    isOpen: () => isOpenFlag,
    setOpen: (v: boolean) => {
      isOpenFlag = v;
    },
    lyricsOpen: cfg.lyricsOpen,
    closeLyrics: cfg.closeLyrics,
    sync,
    render,
    destroyDnd: destroyQueueDragDrop,
  };

  const ctl: QueueController = {
    add: (item) =>
      addToQueue(item, { ensureDom: () => {}, onChanged, toast: cfg.toast, esc: cfg.esc, itemNoun: cfg.itemNoun }),
    remove: (i) => removeFromQueue(i, { onChanged }),
    clear: () => clearQueueAction({ onChanged }),
    playFrom: (i) => playFromQueue(i, { onChanged, playItem: cfg.playItem }),
    open: () => openQueuePanel(panelHooks),
    close: () => closeQueuePanel(panelHooks),
    toggle: () => toggleQueuePanel(panelHooks),
    isOpen: () => isOpenFlag,
    updateBadge,
    updateButtons,
    render,
  };

  initQueueResize({
    handle: el("queue-drag-handle"),
    panel: el("queue-panel"),
    minH: QUEUE_MIN_H,
    heightKey: QUEUE_HEIGHT_KEY,
    isOpen: () => isOpenFlag,
    setUserHeight: (h) => {
      userHeight = h;
    },
  });
  window.addEventListener("resize", () => {
    if (isOpenFlag) sync();
  });
  initQueuePeekHandle({
    handle: el("queue-peek-handle"),
    isOpen: () => isOpenFlag,
    open: ctl.open,
    toggle: ctl.toggle,
  });
  el("queue-close-btn")?.addEventListener("click", ctl.close);
  el("queue-clear-btn")?.addEventListener("click", () => {
    ctl.clear();
    cfg.toast("Warteschlange geleert");
  });
  return ctl;
}

