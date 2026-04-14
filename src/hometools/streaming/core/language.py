"""Language tag parsing for folder and file names.

Detects language markers like ``(engl)``, ``(eng)``, ``(en)``, ``(german)``,
``(de)``, ``(ger)`` etc. in folder names and returns a cleaned name plus an
ISO 639-1 language code.

INSTRUCTIONS (local):
- ``parse_language_tag`` is the single source of truth for language detection
  from folder/file names.  Both the streaming UI and the video organizer
  should use it.
- Add new language patterns to ``_LANG_PATTERNS`` when users have new
  conventions.  Keep patterns case-insensitive.
- The returned ``lang_code`` is always a 2-letter ISO 639-1 code (``en``,
  ``de``, ``fr``, …) or ``""`` when no language is detected.
- ``clean_folder_name`` strips **both** the ``#`` favourite-prefix and
  language tags — use it for display names throughout the UI.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Language patterns — (tag) → ISO 639-1 code
# Ordered by specificity; first match wins.
# ---------------------------------------------------------------------------

_LANG_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # English
    (re.compile(r"\(\s*engl(?:ish)?\s*\)", re.IGNORECASE), "en"),
    (re.compile(r"\(\s*eng\s*\)", re.IGNORECASE), "en"),
    (re.compile(r"\(\s*en\s*\)", re.IGNORECASE), "en"),
    # German
    (re.compile(r"\(\s*german\s*\)", re.IGNORECASE), "de"),
    (re.compile(r"\(\s*deutsch\s*\)", re.IGNORECASE), "de"),
    (re.compile(r"\(\s*ger\s*\)", re.IGNORECASE), "de"),
    (re.compile(r"\(\s*de\s*\)", re.IGNORECASE), "de"),
    # French
    (re.compile(r"\(\s*french\s*\)", re.IGNORECASE), "fr"),
    (re.compile(r"\(\s*fran[cç]ais(?:e)?\s*\)", re.IGNORECASE), "fr"),
    (re.compile(r"\(\s*fr\s*\)", re.IGNORECASE), "fr"),
    # Spanish
    (re.compile(r"\(\s*spanish\s*\)", re.IGNORECASE), "es"),
    (re.compile(r"\(\s*espa[nñ]ol\s*\)", re.IGNORECASE), "es"),
    (re.compile(r"\(\s*es\s*\)", re.IGNORECASE), "es"),
    # Italian
    (re.compile(r"\(\s*italian(?:o)?\s*\)", re.IGNORECASE), "it"),
    (re.compile(r"\(\s*it\s*\)", re.IGNORECASE), "it"),
    # Japanese
    (re.compile(r"\(\s*japanese\s*\)", re.IGNORECASE), "ja"),
    (re.compile(r"\(\s*jap\s*\)", re.IGNORECASE), "ja"),
    (re.compile(r"\(\s*jpn?\s*\)", re.IGNORECASE), "ja"),
    # Korean
    (re.compile(r"\(\s*korean\s*\)", re.IGNORECASE), "ko"),
    (re.compile(r"\(\s*kor?\s*\)", re.IGNORECASE), "ko"),
    # Chinese
    (re.compile(r"\(\s*chinese\s*\)", re.IGNORECASE), "zh"),
    (re.compile(r"\(\s*zh\s*\)", re.IGNORECASE), "zh"),
    # Portuguese
    (re.compile(r"\(\s*portuguese\s*\)", re.IGNORECASE), "pt"),
    (re.compile(r"\(\s*pt\s*\)", re.IGNORECASE), "pt"),
    # Russian
    (re.compile(r"\(\s*russian\s*\)", re.IGNORECASE), "ru"),
    (re.compile(r"\(\s*ru\s*\)", re.IGNORECASE), "ru"),
    # Compound: language + subtitle hint (audio lang only — subtitle extracted by parse_subtitle_hint)
    (re.compile(r"\(\s*engl(?:ish)?\s*,\s*(?:ger|de)sub\s*\)", re.IGNORECASE), "en"),
    (re.compile(r"\(\s*engl(?:ish)?\s*,\s*(?:ger|de)(?:\s*sub(?:s)?)?\s*\)", re.IGNORECASE), "en"),
    (re.compile(r"\(\s*engl(?:ish)?\s*,\s*(?:en|eng)(?:\s*sub(?:s)?)?\s*\)", re.IGNORECASE), "en"),
    # Generic: any recognized lang + any recognized sub lang
    (re.compile(r"\(\s*(?:german|deutsch|ger|de)\s*,\s*\w+(?:\s*sub(?:s)?)?\s*\)", re.IGNORECASE), "de"),
    (re.compile(r"\(\s*(?:french|fran[cç]ais(?:e)?|fr)\s*,\s*\w+(?:\s*sub(?:s)?)?\s*\)", re.IGNORECASE), "fr"),
    (re.compile(r"\(\s*(?:spanish|espa[nñ]ol|es)\s*,\s*\w+(?:\s*sub(?:s)?)?\s*\)", re.IGNORECASE), "es"),
    (re.compile(r"\(\s*(?:italian(?:o)?|it)\s*,\s*\w+(?:\s*sub(?:s)?)?\s*\)", re.IGNORECASE), "it"),
    (re.compile(r"\(\s*(?:japanese|jap|jpn?|ja)\s*,\s*\w+(?:\s*sub(?:s)?)?\s*\)", re.IGNORECASE), "ja"),
    (re.compile(r"\(\s*(?:korean|kor?|ko)\s*,\s*\w+(?:\s*sub(?:s)?)?\s*\)", re.IGNORECASE), "ko"),
    (re.compile(r"\(\s*(?:chinese|zh)\s*,\s*\w+(?:\s*sub(?:s)?)?\s*\)", re.IGNORECASE), "zh"),
    (re.compile(r"\(\s*(?:portuguese|pt)\s*,\s*\w+(?:\s*sub(?:s)?)?\s*\)", re.IGNORECASE), "pt"),
    (re.compile(r"\(\s*(?:russian|ru)\s*,\s*\w+(?:\s*sub(?:s)?)?\s*\)", re.IGNORECASE), "ru"),
]

# Regex that matches *any* known language tag (for stripping from display names)
_ANY_LANG_TAG_RE = re.compile(
    r"\s*\(\s*(?:"
    r"engl(?:ish)?|eng|en"
    r"|german|deutsch|ger|de"
    r"|french|fran[cç]ais(?:e)?|fr"
    r"|spanish|espa[nñ]ol|es"
    r"|italian(?:o)?|it"
    r"|japanese|jap|jpn?|ja"
    r"|korean|kor?|ko"
    r"|chinese|zh"
    r"|portuguese|pt"
    r"|russian|ru"
    r")"
    r"(?:\s*,\s*(?:ger(?:man)?|de(?:utsch)?|eng(?:l(?:ish)?)?|en|fr(?:ench)?|fran[cç]ais(?:e)?|es(?:pa[nñ]ol)?|spanish|it(?:alian(?:o)?)?|ja(?:p(?:anese)?|pn?)?|ko(?:r(?:ean)?)?|zh|chinese|pt|portuguese|ru(?:ssian)?)(?:\s*sub(?:s)?)?)?"
    r"\s*\)",
    re.IGNORECASE,
)


def parse_language_tag(name: str) -> tuple[str, str]:
    """Parse a language tag from a folder or file name.

    Returns ``(clean_name, lang_code)`` where *clean_name* has the language
    tag removed and *lang_code* is a 2-letter ISO 639-1 code (``""`` if
    nothing was detected).

    Examples::

        >>> parse_language_tag("Malcolm in the Middle (engl)")
        ('Malcolm in the Middle', 'en')
        >>> parse_language_tag("Breaking Bad (engl, gersub)")
        ('Breaking Bad', 'en')
        >>> parse_language_tag("Malcolm Mittendrin")
        ('Malcolm Mittendrin', '')
    """
    for pattern, code in _LANG_PATTERNS:
        m = pattern.search(name)
        if m:
            cleaned = name[: m.start()] + name[m.end() :]
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
            return cleaned, code
    return name, ""


def strip_language_tag(name: str) -> str:
    """Remove any language tag from *name*, returning the cleaned string."""
    result = _ANY_LANG_TAG_RE.sub("", name)
    return re.sub(r"\s{2,}", " ", result).strip()


def clean_folder_name(name: str) -> str:
    """Strip ``#`` prefix and language tags for UI display.

    Combines the existing favourites-prefix removal with language tag
    stripping into a single helper.

    Examples::

        >>> clean_folder_name("#Malcolm in the Middle (engl)")
        'Malcolm in the Middle'
        >>> clean_folder_name("#Breaking Bad")
        'Breaking Bad'
        >>> clean_folder_name("Malcolm Mittendrin")
        'Malcolm Mittendrin'
    """
    # Strip leading # (favourites marker)
    if name.startswith("#"):
        name = name[1:]
    # Strip language tag
    name = strip_language_tag(name)
    return name.strip()


# ---------------------------------------------------------------------------
# Subtitle hint detection
# ---------------------------------------------------------------------------

# Patterns: (engl, gersub), (engl, de subs), (japanese, ensub), etc.
# Captures the subtitle-language part from compound tags.
_SUB_HINT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # German subtitles
    (re.compile(r"\(\s*\w+\s*,\s*(?:ger|german|de|deutsch)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)", re.IGNORECASE), "de"),
    # English subtitles
    (re.compile(r"\(\s*\w+\s*,\s*(?:eng|engl(?:ish)?|en)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)", re.IGNORECASE), "en"),
    # French subtitles
    (re.compile(r"\(\s*\w+\s*,\s*(?:fr(?:ench)?|fran[cç]ais(?:e)?)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)", re.IGNORECASE), "fr"),
    # Spanish subtitles
    (re.compile(r"\(\s*\w+\s*,\s*(?:es(?:pa[nñ]ol)?|spanish)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)", re.IGNORECASE), "es"),
    # Italian subtitles
    (re.compile(r"\(\s*\w+\s*,\s*(?:it(?:alian(?:o)?)?)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)", re.IGNORECASE), "it"),
    # Japanese subtitles
    (re.compile(r"\(\s*\w+\s*,\s*(?:ja(?:p(?:anese)?|pn?)?)(?:\s*sub(?:s|title)?(?:s)?)?\s*\)", re.IGNORECASE), "ja"),
]


def parse_subtitle_hint(name: str) -> str:
    """Extract the subtitle language from a compound folder name tag.

    Returns a 2-letter ISO 639-1 code (``""`` if no subtitle hint found).

    Examples::

        >>> parse_subtitle_hint("Breaking Bad (engl, gersub)")
        'de'
        >>> parse_subtitle_hint("Narcos (engl, en subs)")
        'en'
        >>> parse_subtitle_hint("Malcolm in the Middle (engl)")
        ''
        >>> parse_subtitle_hint("Malcolm Mittendrin")
        ''
    """
    for pattern, code in _SUB_HINT_PATTERNS:
        if pattern.search(name):
            return code
    return ""


def parse_language_full(name: str) -> tuple[str, str, str]:
    """Parse both audio language and subtitle language from a folder name.

    Returns ``(clean_name, audio_lang, subtitle_lang)`` where:
    - *clean_name* has the language tag removed
    - *audio_lang* is the main audio language code (``""`` if undetected)
    - *subtitle_lang* is the subtitle language code (``""`` if none)

    This is a convenience wrapper around :func:`parse_language_tag` and
    :func:`parse_subtitle_hint`.

    Examples::

        >>> parse_language_full("Breaking Bad (engl, gersub)")
        ('Breaking Bad', 'en', 'de')
        >>> parse_language_full("Malcolm Mittendrin")
        ('Malcolm Mittendrin', '', '')
    """
    sub_lang = parse_subtitle_hint(name)
    clean_name, audio_lang = parse_language_tag(name)
    return clean_name, audio_lang, sub_lang
