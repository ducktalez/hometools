/** Folder-name language/subtitle detection. Ported from player_js/_queue.py.
 * Regex lookups + flag HTML builders. Flag SVG map (LANG_TO_FLAG, single
 * source of truth in _svg.py) is an explicit param. Bridged onto window by
 * main.ts; legacy keeps thin bare-name wrappers. */

const LANG_DETECT_MAP: [RegExp, string][] = [
  [/\(\s*engl(?:ish)?\s*(?:,\s*(?:ger|de)(?:\s*sub(?:s)?)?)?\s*\)/i, "en"],
  [/\(\s*eng\s*\)/i, "en"],
  [/\(\s*en\s*\)/i, "en"],
  [/\(\s*german\s*\)/i, "de"],
  [/\(\s*deutsch\s*\)/i, "de"],
  [/\(\s*ger\s*\)/i, "de"],
  [/\(\s*de\s*\)/i, "de"],
  [/\(\s*french\s*\)/i, "fr"],
  [/\(\s*fran[cç]ais(?:e)?\s*\)/i, "fr"],
  [/\(\s*fr\s*\)/i, "fr"],
  [/\(\s*spanish\s*\)/i, "es"],
  [/\(\s*espa[nñ]ol\s*\)/i, "es"],
  [/\(\s*es\s*\)/i, "es"],
  [/\(\s*italian(?:o)?\s*\)/i, "it"],
  [/\(\s*it\s*\)/i, "it"],
  [/\(\s*japanese\s*\)/i, "ja"],
  [/\(\s*jap\s*\)/i, "ja"],
  [/\(\s*jpn?\s*\)/i, "ja"],
  [/\(\s*korean\s*\)/i, "ko"],
  [/\(\s*kor?\s*\)/i, "ko"],
  [/\(\s*chinese\s*\)/i, "zh"],
  [/\(\s*zh\s*\)/i, "zh"],
  [/\(\s*portuguese\s*\)/i, "pt"],
  [/\(\s*pt\s*\)/i, "pt"],
  [/\(\s*russian\s*\)/i, "ru"],
  [/\(\s*ru\s*\)/i, "ru"],
];

/** Detect main language hint from a folder/file name, e.g. "(engl)" -> "en". */
export function detectLangFromName(name: string): string {
  for (let i = 0; i < LANG_DETECT_MAP.length; i++) {
    if (LANG_DETECT_MAP[i][0].test(name)) return LANG_DETECT_MAP[i][1];
  }
  return "";
}

/** lang code -> inline SVG markup (LANG_TO_FLAG, single source: _svg.py). */
export type FlagMap = Record<string, string>;

/** Badge spans for each language that has a flag; "" when none. */
export function langBadgesHtml(langs: string[] | null | undefined, flags: FlagMap): string {
  if (!langs || !langs.length) return "";
  let html = "";
  langs.forEach((lc) => {
    const svg = flags[lc];
    if (svg) {
      html += '<span class="lang-badge" title="' + lc.toUpperCase() + '">' + svg + "</span>";
    }
  });
  return html;
}

/** Main-language flag with optional smaller subtitle-flag overlay. */
export function compositeFlagHtml(mainLang: string, subLang: string, flags: FlagMap): string {
  const mainSvg = mainLang && flags[mainLang] ? flags[mainLang] : "";
  if (!mainSvg) return "";
  const subSvg = subLang && flags[subLang] ? flags[subLang] : "";
  if (!subSvg) {
    return '<span class="composite-flag" title="' + (mainLang || "").toUpperCase() + '">' + mainSvg + "</span>";
  }
  return (
    '<span class="composite-flag" title="' + (mainLang || "").toUpperCase() + " + " + (subLang || "").toUpperCase() + ' Sub">' +
    mainSvg +
    '<span class="composite-flag-sub">' + subSvg + "</span>" +
    "</span>"
  );
}
const SUB_DETECT_MAP: [RegExp, string][] = [
  [/\(\s*\w+\s*,\s*(?:ger(?:man)?|de(?:utsch)?)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)/i, "de"],
  [/\(\s*\w+\s*,\s*(?:eng(?:l(?:ish)?)?|en)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)/i, "en"],
  [/\(\s*\w+\s*,\s*(?:fr(?:ench)?|fran[cç]ais(?:e)?)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)/i, "fr"],
  [/\(\s*\w+\s*,\s*(?:es(?:pa[nñ]ol)?|spanish)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)/i, "es"],
  [/\(\s*\w+\s*,\s*(?:it(?:alian(?:o)?)?)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)/i, "it"],
  [/\(\s*\w+\s*,\s*(?:ja(?:p(?:anese)?|pn?)?)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)/i, "ja"],
];

/** Detect subtitle language hint, e.g. "(engl, gersub)" -> "de". */
export function detectSubLangFromName(name: string): string {
  for (let i = 0; i < SUB_DETECT_MAP.length; i++) {
    if (SUB_DETECT_MAP[i][0].test(name)) return SUB_DETECT_MAP[i][1];
  }
  return "";
}

