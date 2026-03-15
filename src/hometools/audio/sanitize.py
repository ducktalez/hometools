"""Audio filename sanitization and identifier extraction.

Pure functions that transform file-name stems – ideal for unit testing.
"""

import copy
import re


def stem_identifier(stem: str) -> list[str]:
    """Progressively clean an audio file stem, returning the history of transformations.

    The last element of the returned list is the final cleaned version.

    Special cases handled:
      - shortest artists: 'JJ - Still', shortest filename 'ss.mp3'
      - Interprets: frei.wild, Mollono.Bass, no_4mat
    """
    history = [stem]

    def sub_and_store(pattern, repl, flags=0):
        new_version = re.sub(pattern, repl, history[-1], flags=flags)
        history.append(new_version)

    # === safe replaces ===
    sub_and_store('&amp;', '&')
    sub_and_store(r'\(152kbit_Opus\)|\(\d{1,3}kbit\_[A-Za-z]+\)', '', flags=re.IGNORECASE)
    sub_and_store(r'\(Official.{0,8}Video\)', '', flags=re.IGNORECASE)
    sub_and_store(r'\(\w*\.[a-zA-Z]{2,5}\)', '', flags=re.IGNORECASE)  # links in filename
    sub_and_store(r'\w*\.(?:com|net|org|co\.uk|de|vu|ru|pl)', '', flags=re.IGNORECASE)
    sub_and_store(
        u"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U00002702-\U000027B0\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937\U00010000-\U0010ffff\u2640-\u2642\u2600-\u2B55"
        u"\u200d\u23cf\u23e9\u231a\ufe0f\u3030]+", '',
        flags=re.IGNORECASE,
    )
    sub_and_store(r'(?<=\W)(featuring|feat\.|feat)\W', 'feat. ', flags=re.IGNORECASE)
    sub_and_store(r'(?<=\W)(produced by|produced|prod\. by|prod by|prod\.|prod)\W', 'prod. ', flags=re.IGNORECASE)
    sub_and_store(r'(?<=(?:\W|\(|\[))(vs\.|vs|versus)', 'vs. ', flags=re.IGNORECASE)
    sub_and_store(r'(?<=\W)(^ )', ' ', flags=re.IGNORECASE)
    sub_and_store(r'\(\s*\)|\[\s*\]', '')
    sub_and_store(r' {2,}', ' ')
    sub_and_store(r'^ +| +$', '')

    return history


def sanitize_track_to_path(s: str) -> list[str]:
    """Sanitize a track stem so it is safe to use as a file-system path component.

    Returns the full transformation history (last element = final result).

    Example::

        >>> sanitize_track_to_path('AC/DC - Highway to Hell')[-1]
        'ACDC - Highway to Hell'
    """
    s0 = copy.deepcopy(s)
    s = re.sub(r'AC/DC', 'ACDC', s)
    s = re.sub(r'"', '', s)
    s = re.sub(r'[/\\<>:|\?\*]', '_', s)
    return stem_identifier(s)


def split_stem(stem: str, min_length: int = 2) -> list[str]:
    """Split a sanitized stem into semantic parts (artist, title, features, …)."""
    cleaned = stem_identifier(stem)[-1]
    parts = re.split(
        r"feat\.|prod\.|vs\.|\(|\[| - |, | & |\)|\]",
        cleaned,
        flags=re.IGNORECASE,
    )
    from hometools.utils import fix_spaces
    parts = [fix_spaces(p) for p in parts]
    return [p for p in parts if len(p) >= min_length]


def split_extreme(stem: str, min_length: int = 3) -> list[str]:
    """Aggressively split a stem, removing common music keywords."""
    parts = split_stem(stem, min_length=min_length)
    cleaned = [
        re.sub(
            r'original|Official|Extended|Radio|vocal|edit|remix|mix|version|release',
            '', p, flags=re.IGNORECASE,
        )
        for p in parts
    ]
    cleaned = [re.sub(r'\W|_', '', p) for p in cleaned]
    return [p for p in set(cleaned) if len(p) > min_length]
