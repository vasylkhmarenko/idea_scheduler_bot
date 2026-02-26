"""Tests for spaCy-based parser."""

import pytest
from unittest.mock import Mock, patch

import ai_parser


class TestSpacyAvailability:
    """Tests for spaCy availability checks."""

    def test_is_spacy_available_with_model(self):
        """Should return True when model is loaded."""
        # Reset cached nlp
        ai_parser._nlp = None
        # This test requires spaCy model to be installed
        result = ai_parser.is_spacy_available()
        # If model is installed, should be True
        # If not installed, should be False (graceful degradation)
        assert isinstance(result, bool)

    def test_is_spacy_available_without_model(self):
        """Should return False when model not found."""
        ai_parser._nlp = None
        # Patch _get_nlp to return None (simulating missing model)
        with patch.object(ai_parser, "_get_nlp", return_value=None):
            assert ai_parser.is_spacy_available() is False


class TestParseWithSpacy:
    """Tests for spaCy parsing function."""

    @pytest.fixture
    def mock_nlp(self):
        """Create a mock spaCy nlp object."""
        mock = Mock()
        return mock

    def test_returns_none_without_model(self):
        """Should return None when spaCy model not available."""
        ai_parser._nlp = None
        with patch.object(ai_parser, "_get_nlp", return_value=None):
            result = ai_parser.parse_with_spacy("Call mom tomorrow")
            assert result is None

    def test_returns_none_without_time_entities(self):
        """Should return None when no DATE/TIME entities found."""
        mock_doc = Mock()
        mock_doc.ents = []  # No entities

        mock_nlp = Mock(return_value=mock_doc)

        with patch.object(ai_parser, "_get_nlp", return_value=mock_nlp):
            result = ai_parser.parse_with_spacy("Hello world")
            assert result is None

    def test_extracts_idea_and_time(self):
        """Should extract idea and time from text."""
        # "Call mom tomorrow" = 17 chars, "tomorrow" is at 9-17
        mock_ent = Mock()
        mock_ent.label_ = "DATE"
        mock_ent.start_char = 9
        mock_ent.end_char = 17
        mock_ent.text = "tomorrow"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        mock_nlp = Mock(return_value=mock_doc)

        with patch.object(ai_parser, "_get_nlp", return_value=mock_nlp):
            result = ai_parser.parse_with_spacy("Call mom tomorrow")
            assert result is not None
            assert result["time_str"] == "tomorrow"
            assert "Call mom" in result["idea"]

    def test_combines_multiple_time_entities(self):
        """Should combine DATE and TIME entities."""
        # "Call mom tomorrow 3pm" = 21 chars
        # "tomorrow" at 9-17, "3pm" at 18-21
        mock_date = Mock()
        mock_date.label_ = "DATE"
        mock_date.start_char = 9
        mock_date.end_char = 17
        mock_date.text = "tomorrow"

        mock_time = Mock()
        mock_time.label_ = "TIME"
        mock_time.start_char = 18
        mock_time.end_char = 21
        mock_time.text = "3pm"

        mock_doc = Mock()
        mock_doc.ents = [mock_date, mock_time]

        mock_nlp = Mock(return_value=mock_doc)

        with patch.object(ai_parser, "_get_nlp", return_value=mock_nlp):
            result = ai_parser.parse_with_spacy("Call mom tomorrow 3pm")
            assert result is not None
            assert "tomorrow" in result["time_str"]
            assert "3pm" in result["time_str"]

    def test_returns_none_for_short_idea(self):
        """Should return None if remaining idea is too short."""
        mock_ent = Mock()
        mock_ent.label_ = "DATE"
        mock_ent.start_char = 0
        mock_ent.end_char = 8
        mock_ent.text = "tomorrow"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        mock_nlp = Mock(return_value=mock_doc)

        with patch.object(ai_parser, "_get_nlp", return_value=mock_nlp):
            result = ai_parser.parse_with_spacy("tomorrow x")
            # "x" is too short (< 3 chars)
            assert result is None


class TestBackwardsCompatibility:
    """Tests for backwards compatibility aliases."""

    def test_parse_with_ai_adds_confidence(self):
        """parse_with_ai should add confidence field."""
        # "Call mom tomorrow" = 17 chars, "tomorrow" at 9-17
        mock_ent = Mock()
        mock_ent.label_ = "DATE"
        mock_ent.start_char = 9
        mock_ent.end_char = 17
        mock_ent.text = "tomorrow"

        mock_doc = Mock()
        mock_doc.ents = [mock_ent]

        mock_nlp = Mock(return_value=mock_doc)

        with patch.object(ai_parser, "_get_nlp", return_value=mock_nlp):
            result = ai_parser.parse_with_ai("Call mom tomorrow")
            assert result is not None
            assert "confidence" in result
            assert result["confidence"] == 0.8

    def test_is_ai_available_alias(self):
        """is_ai_available should be alias for is_spacy_available."""
        with patch.object(ai_parser, "is_spacy_available", return_value=True):
            assert ai_parser.is_ai_available() is True

        with patch.object(ai_parser, "is_spacy_available", return_value=False):
            assert ai_parser.is_ai_available() is False


class TestIntegrationWithRealSpacy:
    """Integration tests with real spaCy model (if installed)."""

    @pytest.fixture
    def reset_nlp(self):
        """Reset cached nlp before each test."""
        ai_parser._nlp = None
        yield
        ai_parser._nlp = None

    def test_real_parse_call_mom_tomorrow(self, reset_nlp):
        """Test with real spaCy model."""
        if not ai_parser.is_spacy_available():
            pytest.skip("spaCy model not installed")

        result = ai_parser.parse_with_spacy("Call mom tomorrow at 3pm")
        assert result is not None
        assert "mom" in result["idea"].lower() or "call" in result["idea"].lower()

    def test_real_parse_meeting_next_week(self, reset_nlp):
        """Test with real spaCy model."""
        if not ai_parser.is_spacy_available():
            pytest.skip("spaCy model not installed")

        result = ai_parser.parse_with_spacy("Schedule meeting next Monday")
        # Result depends on spaCy's NER - may or may not detect "next Monday"
        # This is an integration test to verify no crashes
        assert result is None or isinstance(result, dict)
