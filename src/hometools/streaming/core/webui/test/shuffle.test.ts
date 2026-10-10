import { describe, it, expect, beforeEach } from "vitest";
import { installState, removeState, item } from "./helpers";
import { nextIndex, prevIndex, peekNextIndex, rebuildShuffleQueue, buildWeightedQueue } from "../src/shuffle";

const five = () => [0, 1, 2, 3, 4].map((i) => item("t" + i, { rating: i }));

describe("nextIndex/prevIndex linear", () => {
  it("advances, stops at end without repeat", () => {
    const s = installState({ filteredItems: five(), currentIndex: 3 });
    expect(nextIndex()).toBe(4);
    s.currentIndex = 4;
    expect(nextIndex()).toBe(-1);
  });
  it("wraps with repeat all", () => {
    installState({ filteredItems: five(), currentIndex: 4, repeatMode: "all" });
    expect(nextIndex()).toBe(0);
  });
  it("prev clamps to 0, wraps with repeat all", () => {
    const s = installState({ filteredItems: five(), currentIndex: 0 });
    expect(prevIndex()).toBe(0);
    s.repeatMode = "all";
    expect(prevIndex()).toBe(4);
  });
  it("no bridge -> safe defaults", () => {
    removeState();
    expect(nextIndex()).toBe(-1);
    expect(prevIndex()).toBe(0);
  });
});

describe("shuffle peek/commit", () => {
  let s: ReturnType<typeof installState>;
  beforeEach(() => {
    s = installState({ filteredItems: five(), shuffleMode: "normal", shuffleQueue: [0, 3, 1, 4, 2], shufflePos: 0 });
  });

  it("nextIndex advances shufflePos", () => {
    expect(nextIndex()).toBe(3);
    expect(s.shufflePos).toBe(1);
  });
  it("peek has no side effect; uncommitted peek does not skip", () => {
    const p = peekNextIndex();
    expect(p.index).toBe(3);
    expect(s.shufflePos).toBe(0);
    expect(nextIndex()).toBe(3); // aborted crossfade case
  });
  it("commit advances", () => {
    peekNextIndex().commit();
    expect(s.shufflePos).toBe(1);
  });
  it("stale commit after queue rebuild is a no-op", () => {
    const p = peekNextIndex();
    s.shuffleQueue = [4, 3, 2, 1, 0];
    s.shufflePos = 2;
    p.commit();
    expect(s.shufflePos).toBe(2);
  });
  it("weighted wrap: peek keeps old queue, commit installs fresh one", () => {
    s.shuffleMode = "weighted";
    s.shufflePos = 4;
    const old = s.shuffleQueue;
    const p = peekNextIndex();
    expect(s.shuffleQueue).toBe(old);
    p.commit();
    expect(s.shuffleQueue).not.toBe(old);
    expect(s.shufflePos).toBe(0);
    expect(s.shuffleQueue[0]).toBe(p.index);
  });
});

describe("queue builders", () => {
  it("weighted: rating r -> r+1 slots", () => {
    const q = buildWeightedQueue(five());
    expect(q.length).toBe(1 + 2 + 3 + 4 + 5);
    expect(q.filter((i) => i === 4).length).toBe(5);
  });
  it("rebuildShuffleQueue puts startIndex first", () => {
    const s = installState({ filteredItems: five(), shuffleMode: "normal" });
    rebuildShuffleQueue(3);
    expect(s.shuffleQueue[0]).toBe(3);
    expect([...s.shuffleQueue].sort()).toEqual([0, 1, 2, 3, 4]);
    expect(s.shufflePos).toBe(0);
  });
  it("rebuildShuffleQueue off -> cleared", () => {
    const s = installState({ filteredItems: five(), shuffleMode: false, shuffleQueue: [1], shufflePos: 0 });
    rebuildShuffleQueue(0);
    expect(s.shuffleQueue).toEqual([]);
    expect(s.shufflePos).toBe(-1);
  });
});

