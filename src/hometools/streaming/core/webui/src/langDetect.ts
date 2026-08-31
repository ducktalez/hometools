/** Folder-name language/subtitle detection. Ported from player_js/_queue.py.
 * Pure regex lookups, no window reads. Bridged onto window by main.ts;
 * langBadgesHtml/compositeFlagHtml (need LANG_TO_FLAG SVG markup, single
 * source of truth in _svg.py) stay in Python and call these by bare name. */

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

