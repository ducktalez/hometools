/**
 * Folder-grid card HTML. Ported from `_folder_browse.py` (folder + file
 * cards in the render loop). Pure: all legacy globals come in via `opts`.
 */

import type { FolderEntry } from "./folderContents";

export interface FolderCardOpts {
  escHtml: (s: unknown) => string;
  viewMode: string;
  showOrigNames: boolean;
  isVideo: boolean;
  itemNoun: string;
  defaultLang: string;
  audiobookDirs: string[];
  langNames: Record<string, string>;
  folderPlaceholder: string;
  filePlaceholder: string;
  icStar: string;
  icFolderPlay: string;
  compositeFlagHtml: (lang: string, subLang: string) => string;
  langBadgesHtml: (langs: string[]) => string;
}

export function folderCardHtml(f: FolderEntry, o: FolderCardOpts): string {
  const esc = o.escHtml;
  const noun = f.count !== 1 ? o.itemNoun + "s" : o.itemNoun;
  const thumbSrc =
    o.viewMode !== "list"
      ? f.thumbnail_lg_url || f.thumbnail_url || o.folderPlaceholder
      : f.thumbnail_url || o.folderPlaceholder;
  const displayLabel = o.showOrigNames ? f.name : f.displayName;
  const favBadge =
    f.isFavorite && !o.showOrigNames ? '<span class="fav-badge" title="Favorit">' + o.icStar + "</span>" : "";
  let langBadges = !o.showOrigNames ? o.langBadgesHtml(f.languages) : "";
  const isAudiobook = o.audiobookDirs.some((d) => f.name.toLowerCase().startsWith(d.toLowerCase()));
  const variants = f.variants;
  const hasVariants = !!(variants && variants.length > 1);
  const extraClass =
    (f.isFavorite ? " fav-folder" : "") + (isAudiobook ? " audiobook-folder" : "") + (hasVariants ? " multi-lang-folder" : "");
  const variantsAttr = hasVariants ? ' data-variants="' + esc(JSON.stringify(variants)) + '"' : "";

  // Video: single primary-language corner flag; suppress inline badge.
  let cornerFlagHtml = "";
  if (o.isVideo && !o.showOrigNames && !hasVariants) {
    const primaryLang = (f.languages && f.languages[0]) || o.defaultLang;
    const pf = o.compositeFlagHtml(primaryLang, f.subLang || "");
    if (pf) cornerFlagHtml = '<span class="folder-lang-corner">' + pf + "</span>";
    langBadges = "";
  }

  let countContent: string;
  if (hasVariants && !o.showOrigNames && variants) {
    const sortedV = variants.slice().sort((a, b) => {
      if (a.lang === o.defaultLang && b.lang !== o.defaultLang) return -1;
      if (b.lang === o.defaultLang && a.lang !== o.defaultLang) return 1;
      return (a.lang || "").localeCompare(b.lang || "");
    });
    countContent = "";
    sortedV.forEach((v) => {
      const flag = o.compositeFlagHtml(v.lang, v.subLang);
      if (flag) {
        countContent +=
          '<button class="lang-select-btn" data-variant-name="' + esc(v.name) + '" title="' +
          esc(
            (o.langNames[v.lang] || v.lang || "") +
              (v.subLang ? " + " + (o.langNames[v.subLang] || v.subLang) + " Sub" : "") +
              " (" + v.count + ")"
          ) +
          '">' + flag + '<span class="lang-select-count">' + v.count + "</span></button>";
      }
    });
    if (!countContent) countContent = f.count + " " + noun;
  } else {
    countContent = f.count + " " + noun;
  }

  return (
    '<div class="folder-card' + extraClass + '" data-folder="' + esc(f.name) + '"' + variantsAttr + ">" +
    favBadge +
    cornerFlagHtml +
    '<img class="folder-thumb" src="' + esc(thumbSrc) + '" alt="" loading="lazy">' +
    '<div class="folder-name">' + esc(displayLabel) + (langBadges && !hasVariants ? " " + langBadges : "") + "</div>" +
    '<div class="folder-count">' + countContent + "</div>" +
    '<button class="folder-play-btn" title="Play all">' + o.icFolderPlay + "</button>" +
    "</div>"
  );
}

export function fileCardHtml(it: LegacyMediaItem, idx: number, o: FolderCardOpts): string {
  const esc = o.escHtml;
  const thumbSrc =
    o.viewMode !== "list"
      ? (it.thumbnail_lg_url as string) || (it.thumbnail_url as string) || o.filePlaceholder
      : (it.thumbnail_url as string) || o.filePlaceholder;
  const rating = Number(it.rating) || 0;
  const ratingBar = rating > 0 ? '<div class="rating-bar" style="width:' + (rating / 5) * 100 + '%"></div>' : "";
  return (
    '<div class="folder-card file-card" data-file-idx="' + idx + '">' +
    '<div class="thumb-wrap folder-thumb-wrap">' +
    '<img class="folder-thumb" src="' + esc(thumbSrc) + '" alt="" loading="lazy">' +
    ratingBar + "</div>" +
    '<div class="folder-name">' + esc(it.title) + "</div>" +
    '<div class="folder-count">' + esc(it.artist || "") + "</div>" +
    "</div>"
  );
}

