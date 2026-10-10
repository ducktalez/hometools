/**
 * Folder-grid contents of one path level: direct sub-folders (aggregated,
 * multi-language variants merged) + loose files.
 *
 * Ported 1:1 from `player_js/_queue.py::contentsAt(path)`. Explicit params:
 * `allItems` (was closure read via itemsUnder) and `langGroups`
 * (was `LANG_GROUPS = CFG.languageGroups`). Legacy keeps a bare-name
 * wrapper `contentsAt(path)` so its call sites stay unchanged.
 */

import { itemsUnder } from "./catalogQuery";
import { cleanFolderName } from "./breadcrumb";
import { detectLangFromName, detectSubLangFromName } from "./langDetect";

/** Synology/NAS system folders never shown in the grid. */
export const IGNORED_FOLDERS: Record<string, boolean> = { "#recycle": true, "@eaDir": true };

export interface FolderVariant {
  name: string;
  lang: string;
  subLang: string;
  count: number;
}

export interface FolderEntry {
  name: string;
  displayName: string;
  isFavorite: boolean;
  count: number;
  thumbnail_url: string;
  thumbnail_lg_url: string;
  languages: string[];
  /** Only on un-merged entries (legacy shape). */
  subLang?: string;
  /** null = single folder; array = merged language variants. */
  variants: FolderVariant[] | null;
}

export interface FolderContents {
  folders: FolderEntry[];
  files: LegacyMediaItem[];
}

export function contentsAt(
  path: string,
  allItems: LegacyMediaItem[],
  langGroups: Record<string, string>
): FolderContents {
  const items = itemsUnder(path, allItems);
  const folderMap: Record<string, number> = {};
  const folderThumb: Record<string, string> = {};
  const folderThumbLg: Record<string, string> = {};
  const folderLangs: Record<string, Record<string, boolean>> = {};
  const folderSubLangs: Record<string, string> = {};
  const files: LegacyMediaItem[] = [];
  const off = path ? path.length + 1 : 0;

  items.forEach((it) => {
    const rest = it.relative_path.substring(off);
    const slash = rest.indexOf("/");
    if (slash < 0) {
      files.push(it);
      return;
    }
    const name = rest.substring(0, slash);
    if (IGNORED_FOLDERS[name]) return;
    folderMap[name] = (folderMap[name] || 0) + 1;
    const thumb = it.thumbnail_url as string | undefined;
    const thumbLg = it.thumbnail_lg_url as string | undefined;
    if (!folderThumb[name] && thumb) folderThumb[name] = thumb;
    if (!folderThumbLg[name] && thumbLg) folderThumbLg[name] = thumbLg;
    // Languages: item metadata + folder-name detection
    if (!folderLangs[name]) folderLangs[name] = {};
    const lang = it.language as string | undefined;
    if (lang) folderLangs[name][lang] = true;
    const folderLang = detectLangFromName(name);
    if (folderLang) folderLangs[name][folderLang] = true;
    // Subtitle language: first item value, else folder-name detection
    if (!folderSubLangs[name]) folderSubLangs[name] = "";
    const subLang = it.subtitle_language as string | undefined;
    if (!folderSubLangs[name] && subLang) folderSubLangs[name] = subLang;
    if (!folderSubLangs[name]) {
      const detSub = detectSubLangFromName(name);
      if (detSub) folderSubLangs[name] = detSub;
    }
  });

  const folders: FolderEntry[] = Object.keys(folderMap)
    .sort((a, b) => {
      // Favorites (#-prefixed) first, then alphabetical
      const aFav = a.charAt(0) === "#";
      const bFav = b.charAt(0) === "#";
      if (aFav !== bFav) return aFav ? -1 : 1;
      return a.localeCompare(b);
    })
    .map((n) => ({
      name: n,
      displayName: cleanFolderName(n),
      isFavorite: n.charAt(0) === "#",
      count: folderMap[n],
      thumbnail_url: folderThumb[n] || "",
      thumbnail_lg_url: folderThumbLg[n] || "",
      languages: folderLangs[n] ? Object.keys(folderLangs[n]).sort() : [],
      subLang: folderSubLangs[n] || "",
      variants: null,
    }));

  // ── Multi-language merge: group by langGroups[name] or displayName ──
  const mergeMap: Record<string, FolderEntry[]> = {};
  folders.forEach((f) => {
    const key = langGroups[f.name] || f.displayName;
    if (!mergeMap[key]) mergeMap[key] = [];
    mergeMap[key].push(f);
  });

  const merged: FolderEntry[] = [];
  Object.keys(mergeMap).forEach((key) => {
    const group = mergeMap[key];
    if (group.length === 1) {
      merged.push(group[0]);
      return;
    }
    // Primary: first favorite wins; else LAST variant without language tag; else first
    let primary = group[0];
    for (let gi = 0; gi < group.length; gi++) {
      if (group[gi].isFavorite) {
        primary = group[gi];
        break;
      }
      if (!detectLangFromName(group[gi].name) && !langGroups[group[gi].name]) primary = group[gi];
    }
    const allLangs: Record<string, boolean> = {};
    let totalCount = 0;
    const variants: FolderVariant[] = [];
    group.forEach((g) => {
      totalCount += g.count;
      g.languages.forEach((lc) => {
        allLangs[lc] = true;
      });
      const lang = g.languages.length ? g.languages[0] : detectLangFromName(g.name) || "";
      const subLang = detectSubLangFromName(g.name) || g.subLang || "";
      variants.push({ name: g.name, lang, subLang, count: g.count });
    });
    merged.push({
      name: primary.name,
      displayName: primary.displayName,
      isFavorite: group.some((g) => g.isFavorite),
      count: totalCount,
      thumbnail_url: primary.thumbnail_url || group[1].thumbnail_url || "",
      thumbnail_lg_url: primary.thumbnail_lg_url || group[1].thumbnail_lg_url || "",
      languages: Object.keys(allLangs).sort(),
      variants,
    });
  });

  return { folders: merged, files };
}

