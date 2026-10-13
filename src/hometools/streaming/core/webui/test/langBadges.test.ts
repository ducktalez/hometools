import { describe, it, expect } from "vitest";
import { langBadgesHtml, compositeFlagHtml } from "../src/langDetect";

const flags = { de: "<svg>DE</svg>", en: "<svg>EN</svg>" };

describe("langBadgesHtml", () => {
  it("empty/null langs -> empty string", () => {
    expect(langBadgesHtml(null, flags)).toBe("");
    expect(langBadgesHtml([], flags)).toBe("");
  });

  it("one badge per known lang, unknown skipped", () => {
    const html = langBadgesHtml(["de", "xx", "en"], flags);
    expect(html).toBe(
      '<span class="lang-badge" title="DE"><svg>DE</svg></span>' +
        '<span class="lang-badge" title="EN"><svg>EN</svg></span>',
    );
  });
});

describe("compositeFlagHtml", () => {
  it("unknown main lang -> empty string", () => {
    expect(compositeFlagHtml("xx", "de", flags)).toBe("");
    expect(compositeFlagHtml("", "de", flags)).toBe("");
  });

  it("main only", () => {
    expect(compositeFlagHtml("de", "", flags)).toBe(
      '<span class="composite-flag" title="DE"><svg>DE</svg></span>',
    );
  });

  it("main + sub overlay", () => {
    const html = compositeFlagHtml("en", "de", flags);
    expect(html).toContain('title="EN + DE Sub"');
    expect(html).toContain('<span class="composite-flag-sub"><svg>DE</svg></span>');
  });

  it("unknown sub falls back to main only", () => {
    expect(compositeFlagHtml("en", "xx", flags)).not.toContain("composite-flag-sub");
  });
});

