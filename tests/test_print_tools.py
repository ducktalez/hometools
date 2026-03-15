"""Tests for hometools.print_tools."""

from hometools.print_tools import Colors, highlight_removed


class TestHighlightRemoved:

    def test_no_changes(self):
        result = highlight_removed("hello", "hello")
        assert result == "hello"

    def test_removal_highlighted(self):
        result = highlight_removed("hello world", "hello")
        assert Colors.RED in result
        assert Colors.ENDC in result

    def test_empty_strings(self):
        result = highlight_removed("", "")
        assert result == ""

    def test_complete_removal(self):
        result = highlight_removed("removed", "")
        assert Colors.RED in result
        assert "removed" in result
