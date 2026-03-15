"""Tests for hometools.video.organizer -- pure helper functions."""

import pytest

from hometools.video.organizer import (
    re_umlaute_replace,
    sanitize_path,
    serie_path_to_numbers,
    split_for_search,
)
from pathlib import Path


class TestSplitForSearch:

    def test_basic_split(self):
        parts = split_for_search('The Matrix 1999')
        assert 'The' in parts
        assert 'Matrix' in parts

    def test_removes_resolution(self):
        parts = split_for_search('Movie 1080p Something')
        joined = ' '.join(parts)
        assert '1080p' not in joined.lower()

    def test_removes_codec_tags(self):
        parts = split_for_search('Movie x264 BluRay DD51')
        joined = ' '.join(parts)
        assert 'x264' not in joined
        assert 'BluRay' not in joined

    def test_removes_tmdbid(self):
        parts = split_for_search('Movie [tmdbid-12345]')
        joined = ' '.join(parts)
        assert 'tmdbid' not in joined.lower()

    def test_removes_engl_tag(self):
        parts = split_for_search('Movie (engl) Title')
        joined = ' '.join(parts)
        assert 'engl' not in joined.lower()


class TestReUmlauteReplace:

    def test_replaces_lowercase_umlauts(self):
        assert re_umlaute_replace('\u00fcber') == 'ueber'
        assert re_umlaute_replace('sch\u00f6n') == 'schoen'
        assert re_umlaute_replace('Stra\u00dfe') == 'Strasse'

    def test_replaces_uppercase_umlauts(self):
        assert re_umlaute_replace('\u00c4rger') == 'AErger'

    def test_reverse_lowercase(self):
        assert re_umlaute_replace('ueber', reverse=True) == '\u00fcber'

    def test_reverse_uppercase(self):
        assert re_umlaute_replace('AErger', reverse=True) == '\u00c4rger'

    def test_no_umlauts(self):
        assert re_umlaute_replace('hello world') == 'hello world'


class TestSanitizePath:

    def test_replaces_invalid_chars(self):
        result = sanitize_path('Movie: The Best <One>')
        assert ':' not in result
        assert '<' not in result
        assert '>' not in result

    def test_replaces_windows_reserved(self):
        result = sanitize_path('CON')
        assert result != 'CON'

    def test_strips_trailing_dots_spaces(self):
        result = sanitize_path('movie name...')
        assert not result.endswith('.')

    def test_normal_path_unchanged(self):
        result = sanitize_path('A Nice Movie Title')
        assert result == 'A Nice Movie Title'


class TestSeriePathToNumbers:

    def test_standard_pattern(self):
        p = Path('Breaking.Bad.S02E03.Something.mp4')
        result = serie_path_to_numbers(p)
        assert result == {'season': 2, 'episode': 3}

    def test_lowercase(self):
        p = Path('show.s01e10.title.mkv')
        result = serie_path_to_numbers(p)
        assert result == {'season': 1, 'episode': 10}

    def test_large_episode_number(self):
        p = Path('Anime S01E1034 Title.mp4')
        result = serie_path_to_numbers(p)
        assert result == {'season': 1, 'episode': 1034}

    def test_no_pattern_raises(self):
        p = Path('Movie Without Season Info.mp4')
        with pytest.raises(ValueError, match='No S##E## pattern'):
            serie_path_to_numbers(p)
