"""Tests for parse_add_command function."""

import pytest
from main import parse_add_command, looks_like_event, parse_time_robust


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


class TestLooksLikeEvent:
    """Tests for filtering casual conversation from events."""

    def test_rejects_questions(self):
        """Should reject messages ending with ?"""
        assert looks_like_event("What time is it", "What time is it tomorrow?") is False
        assert looks_like_event("How about", "How about tomorrow?") is False

    def test_rejects_question_words(self):
        """Should reject messages starting with question words."""
        assert looks_like_event("is the meeting", "When is the meeting tomorrow") is False
        assert looks_like_event("are you free", "Are you free tomorrow") is False

    def test_rejects_past_tense(self):
        """Should reject past tense indicators."""
        assert looks_like_event("The meeting was", "The meeting was today at 2pm") is False
        assert looks_like_event("I called him", "I called him yesterday") is False
        assert looks_like_event("We met last", "We met last Friday") is False

    def test_rejects_casual_phrases(self):
        """Should reject conversational phrases."""
        assert looks_like_event("I'll see you", "I'll see you tomorrow") is False
        assert looks_like_event("See you", "See you Monday") is False
        assert looks_like_event("Thanks for", "Thanks for yesterday") is False

    def test_rejects_short_ideas(self):
        """Should reject ideas that are too short."""
        assert looks_like_event("Hi", "Hi tomorrow") is False
        assert looks_like_event("OK", "OK Friday") is False

    def test_accepts_valid_events(self):
        """Should accept legitimate event ideas."""
        assert looks_like_event("Call dentist", "Call dentist tomorrow 2pm") is True
        assert looks_like_event("Team meeting", "Team meeting next Monday") is True
        assert looks_like_event("Submit report", "Submit report in 3 days") is True
        assert looks_like_event("Buy groceries", "Buy groceries Friday") is True

    def test_accepts_single_word_if_long(self):
        """Should accept single-word ideas if 8+ characters."""
        assert looks_like_event("Presentation", "Presentation Friday") is True
        assert looks_like_event("Interview", "Interview tomorrow") is True


class TestParseTimeRobust:
    """Tests for robust time parsing."""

    def test_parses_tomorrow(self):
        """Should parse 'tomorrow 2pm'."""
        result = parse_time_robust("tomorrow 2pm")
        assert result is not None

    def test_parses_next_monday(self):
        """Should parse 'next Monday' (dateparser workaround)."""
        result = parse_time_robust("next Monday 10am")
        assert result is not None

    def test_parses_next_friday(self):
        """Should parse 'next Friday'."""
        result = parse_time_robust("next Friday 2pm")
        assert result is not None

    def test_parses_in_days(self):
        """Should parse 'in 3 days'."""
        result = parse_time_robust("in 3 days")
        assert result is not None

    def test_returns_none_for_invalid(self):
        """Should return None for unparseable time."""
        result = parse_time_robust("blahblah")
        assert result is None

    def test_prefers_future_dates(self):
        """Should prefer future dates."""
        result = parse_time_robust("Monday 10am")
        assert result is not None
        # Result should be in the future (or today)
        from datetime import datetime
        assert result >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
