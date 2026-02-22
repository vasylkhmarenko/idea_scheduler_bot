"""Tests for OAuth state handling."""

import pytest

from oauth import parse_oauth_state, generate_oauth_state
import db


class TestOAuthStateParsing:
    """Tests for OAuth state string parsing."""

    def test_parse_valid_state(self):
        """Should parse valid state string."""
        state = "123456:abc123def456"
        result = parse_oauth_state(state)

        assert result is not None
        user_id, token = result
        assert user_id == 123456
        assert token == "abc123def456"

    def test_parse_state_with_colons_in_token(self):
        """Should handle colons in token part."""
        state = "123456:token:with:colons"
        result = parse_oauth_state(state)

        assert result is not None
        user_id, token = result
        assert user_id == 123456
        assert token == "token:with:colons"

    def test_parse_invalid_state_no_colon(self):
        """Should return None for state without colon."""
        result = parse_oauth_state("invalid_state")
        assert result is None

    def test_parse_invalid_state_non_numeric_user(self):
        """Should return None for non-numeric user_id."""
        result = parse_oauth_state("abc:token123")
        assert result is None

    def test_parse_empty_state(self):
        """Should return None for empty state."""
        result = parse_oauth_state("")
        assert result is None

    def test_parse_none_state(self):
        """Should return None for None input."""
        result = parse_oauth_state(None)
        assert result is None


class TestOAuthStateGeneration:
    """Tests for OAuth state generation."""

    def test_generate_state_format(self, temp_db, sample_user_id):
        """Should generate state in correct format."""
        db.add_user(sample_user_id)
        state = generate_oauth_state(sample_user_id)

        # State should be "user_id:random_token"
        assert ":" in state
        parts = state.split(":", 1)
        assert parts[0] == str(sample_user_id)
        assert len(parts[1]) > 20  # Token should be reasonably long

    def test_generate_state_unique(self, temp_db, sample_user_id):
        """Should generate unique states."""
        db.add_user(sample_user_id)

        state1 = generate_oauth_state(sample_user_id)
        state2 = generate_oauth_state(sample_user_id)

        assert state1 != state2

    def test_generate_state_stored_in_db(self, temp_db, sample_user_id):
        """Should store state in database."""
        db.add_user(sample_user_id)
        state = generate_oauth_state(sample_user_id)

        # Verify state is stored and verifiable
        assert db.verify_oauth_state(sample_user_id, state) is True

    def test_generate_state_parseable(self, temp_db, sample_user_id):
        """Generated state should be parseable."""
        db.add_user(sample_user_id)
        state = generate_oauth_state(sample_user_id)

        result = parse_oauth_state(state)
        assert result is not None
        parsed_user_id, _ = result
        assert parsed_user_id == sample_user_id
