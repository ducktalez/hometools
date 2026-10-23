import { describe, it, expect } from "vitest";
import { playerBarActionsHtml, bpmAdjustMenuHtml } from "../src/playerBarHtml";

const esc = (s: unknown) => String(s).replace(/</g, "&lt;");
const t = { relative_path: "a/b.mp3", title: "T<" } as never;

describe("playerBarActionsHtml", () => {
  it("normal mode: kebab only", () => {
    const h = playerBarActionsHtml(t, ["a"], "a", false, esc, "D", "TR");
    expect(h).toContain('id="player-bar-kebab"');
    expect(h).toContain('data-title="T&lt;"');
    expect(h).not.toContain("player-bar-trash");
    expect(h).not.toContain("select");
  });
  it("mover mode: select (current disabled), trash + kebab row", () => {
    const h = playerBarActionsHtml(t, ["a", "b"], "a", true, esc, "D", "TR");
    expect(h).toContain('<option value="a" disabled>a</option>');
    expect(h).toContain('<option value="b">b</option>');
    expect(h).toContain("player-bar-trash");
    expect(h.match(/player-bar-actions-row/g)).toHaveLength(2);
    expect(h.indexOf("player-bar-trash")).toBeLessThan(h.indexOf("player-bar-kebab"));
  });
  it("mover mode without folders: no select row", () => {
    const h = playerBarActionsHtml(t, [], "", true, esc, "D", "TR");
    expect(h).not.toContain("player-bar-move-select");
    expect(h.match(/player-bar-actions-row/g)).toHaveLength(1);
  });
});

describe("bpmAdjustMenuHtml", () => {
  const ic = { chevronsDown: "DN", refresh: "RF", chevronsUp: "UP" };
  it("known bpm", () => {
    const h = bpmAdjustMenuHtml(85.4, ic);
    expect(h).toContain("85 BPM");
    expect(h).toContain('value="85"');
    expect(h).not.toContain(" disabled");
    expect(h).toContain("DN<span>Langsamer");
    expect(h).toContain("UP<span>Schneller");
  });
  it("unknown bpm disables slower/faster", () => {
    const h = bpmAdjustMenuHtml(0, ic);
    expect(h).toContain("BPM unbekannt");
    expect(h).toContain('value=""');
    expect(h.match(/ disabled/g)).toHaveLength(2);
  });
});

