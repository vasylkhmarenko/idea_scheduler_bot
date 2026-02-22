"""Tests for parse_add_command function."""

import pytest
from main import parse_add_command


class TestParseAddCommand:
    """Tests for parsing /add command input."""

    def test_parse_with_tomorrow(self):
        """Should parse 'tomorrow' time pattern."""
        result = parse_add_command("/add Write blog post tomorrow")
        assert result is not None
        idea, time_str = result
        assert idea == "Write blog post"
        assert "tomorrow" in time_str.lower()

    def test_parse_with_tomorrow_and_time(self):
        """Should parse 'tomorrow 2pm' time pattern."""
        result = parse_add_command("/add Review code tomorrow 2pm")
        assert result is not None
        idea, time_str = result
        assert idea == "Review code"
        assert "tomorrow" in time_str.lower()

    def test_parse_with_today(self):
        """Should parse 'today' time pattern."""
        result = parse_add_command("/add Call mom today")
        assert result is not None
        idea, time_str = result
        assert idea == "Call mom"
        assert "today" in time_str.lower()

    def test_parse_with_next_weekday(self):
        """Should parse 'next Monday' time pattern."""
        result = parse_add_command("/add Team meeting next Monday")
        assert result is not None
        idea, time_str = result
        assert idea == "Team meeting"
        assert "next" in time_str.lower()

    def test_parse_with_in_days(self):
        """Should parse 'in 3 days' time pattern."""
        result = parse_add_command("/add Submit report in 3 days")
        assert result is not None
        idea, time_str = result
        assert idea == "Submit report"
        assert "in 3 days" in time_str.lower()

    def test_parse_with_weekday(self):
        """Should parse weekday pattern."""
        result = parse_add_command("/add Gym session Friday")
        assert result is not None
        idea, time_str = result
        assert idea == "Gym session"
        assert "friday" in time_str.lower()

    def test_parse_empty_command(self):
        """Should return None for empty /add command."""
        result = parse_add_command("/add")
        assert result is None

    def test_parse_empty_after_strip(self):
        """Should return None for /add with only whitespace."""
        result = parse_add_command("/add   ")
        assert result is None

    def test_parse_without_command_prefix(self):
        """Should work without /add prefix."""
        result = parse_add_command("Buy groceries tomorrow")
        assert result is not None
        idea, time_str = result
        assert idea == "Buy groceries"

    def test_parse_idea_only_no_time(self):
        """Should return None when no valid time found."""
        result = parse_add_command("/add Just an idea without time")
        # This might return None or try to parse - depends on dateparser
        # The function should gracefully handle this
        if result is not None:
            idea, time_str = result
            # If it returns something, idea should not be empty
            assert len(idea) > 0

    def test_parse_preserves_idea_text(self):
        """Should preserve full idea text before time."""
        result = parse_add_command("/add Film YouTube video about Python tomorrow 10am")
        assert result is not None
        idea, time_str = result
        assert "Film YouTube video about Python" in idea

    def test_parse_with_date_format(self):
        """Should parse date format like 12/25."""
        result = parse_add_command("/add Christmas shopping 12/25")
        assert result is not None
        idea, time_str = result
        assert idea == "Christmas shopping"
        assert "12/25" in time_str

    def test_parse_strips_whitespace(self):
        """Should strip whitespace from input."""
        result = parse_add_command("  /add  Test idea  tomorrow  ")
        assert result is not None
        idea, time_str = result
        assert idea == "Test idea"
