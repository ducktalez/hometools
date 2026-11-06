import { describe, it, expect, vi } from "vitest";
import { installState, item } from "./helpers";
import { queueAdd, queueRemoveAt, queueClear, queueMove, queueIndexOf, resolveNext, removeFromQueue, clearQueueAction, playFromQueue, addToQueue } from "../src/queue";

describe("addToQueue", () => {
  const hooks = () => ({ ensureDom: vi.fn(), onChanged: vi.fn(), toast: vi.fn(), esc: (s: unknown) => String(s), itemNoun: "track" });
  it("adds, refreshes, toasts with title", () => {
    const s = installState();
    const h = hooks();
    addToQueue(item("a", { title: "A" }), h);
    expect(s.userQueue.length).toBe(1);
    expect(h.onChanged).toHaveBeenCalled();
    expect(h.toast.mock.calls[0][0]).toContain("A");
  });
  it("duplicate -> notice only; invalid -> silent", () => {
    installState({ userQueue: [item("a")] });
    const h = hooks();
    addToQueue(item("a"), h);
    expect(h.toast).toHaveBeenCalledWith("Bereits in der Warteschlange");
    expect(h.onChanged).not.toHaveBeenCalled();
    const h2 = hooks();
    addToQueue(null, h2);
    expect(h2.toast).not.toHaveBeenCalled();
  });
});

describe("queue actions", () => {
  it("removeFromQueue/clearQueueAction fire onChanged only on change", () => {
    installState({ userQueue: [item("a")] });
    const onChanged = vi.fn();
    removeFromQueue(9, { onChanged });
    expect(onChanged).not.toHaveBeenCalled();
    removeFromQueue(0, { onChanged });
    clearQueueAction({ onChanged });
    expect(onChanged).toHaveBeenCalledTimes(2);
  });
  it("playFromQueue uses filteredItems index when present, else -1", () => {
    const f = item("b");
    const s = installState({ userQueue: [item("b"), item("z")], filteredItems: [item("a"), f] });
    const h = { onChanged: vi.fn(), playItem: vi.fn() };
    playFromQueue(0, h);
    expect(h.playItem).toHaveBeenLastCalledWith(f, 1);
    playFromQueue(0, h);
    expect(h.playItem.mock.calls[1][1]).toBe(-1);
    expect(s.userQueue).toEqual([]);
    playFromQueue(0, h);
    expect(h.playItem).toHaveBeenCalledTimes(2);
  });
});

describe("queue ops", () => {
  it("add: slim entry, default media type, duplicate + invalid detection", () => {
    const s = installState();
    expect(queueAdd(item("a", { title: "A", extra: 1 }), "track")).toBe("added");
    expect(s.userQueue[0]).toMatchObject({ relative_path: "a", title: "A", media_type: "track", rating: 0 });
    expect(s.userQueue[0]).not.toHaveProperty("extra");
    expect(queueAdd(item("a"), "track")).toBe("duplicate");
    expect(queueAdd(null, "track")).toBe("invalid");
    expect(s.userQueue.length).toBe(1);
  });
  it("removeAt returns entry, null out of range", () => {
    const s = installState({ userQueue: [item("a"), item("b")] });
    expect(queueRemoveAt(5)).toBeNull();
    expect(queueRemoveAt(0)?.relative_path).toBe("a");
    expect(s.userQueue.map((q) => q.relative_path)).toEqual(["b"]);
  });
  it("clear reassigns", () => {
    const s = installState({ userQueue: [item("a")] });
    const old = s.userQueue;
    queueClear();
    expect(s.userQueue).toEqual([]);
    expect(s.userQueue).not.toBe(old);
  });
  it("move reorders in place, ignores bad indices", () => {
    const s = installState({ userQueue: [item("a"), item("b"), item("c")] });
    queueMove(0, 2);
    expect(s.userQueue.map((q) => q.relative_path)).toEqual(["b", "c", "a"]);
    queueMove(9, 0);
    queueMove(1, 1);
    expect(s.userQueue.map((q) => q.relative_path)).toEqual(["b", "c", "a"]);
  });
  it("indexOf", () => {
    expect(queueIndexOf([item("a"), item("b")], "b")).toBe(1);
    expect(queueIndexOf(null, "b")).toBe(-1);
  });
});

describe("resolveNext", () => {
  it("user queue first, not consumed", () => {
    const s = installState({ filteredItems: [item("x")], userQueue: [item("q")] });
    const n = resolveNext();
    expect(n).toMatchObject({ index: -1, fromQueue: true });
    expect(n?.item.relative_path).toBe("q");
    expect(s.userQueue.length).toBe(1);
  });
  it("linear next, null at end", () => {
    const s = installState({ filteredItems: [item("a"), item("b")], currentIndex: 0 });
    expect(resolveNext()?.index).toBe(1);
    s.currentIndex = 1;
    expect(resolveNext()).toBeNull();
  });
  it("shuffle: no advance until commit", () => {
    const s = installState({
      filteredItems: [item("a"), item("b"), item("c")],
      shuffleMode: "normal",
      shuffleQueue: [2, 0, 1],
      shufflePos: 0,
    });
    const n = resolveNext();
    expect(n?.index).toBe(0);
    expect(s.shufflePos).toBe(0);
    n?.commit();
    expect(s.shufflePos).toBe(1);
  });
});

