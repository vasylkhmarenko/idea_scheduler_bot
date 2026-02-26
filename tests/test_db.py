"""Tests for database operations."""

import pytest
from datetime import datetime, timedelta

import db


class TestUserOperations:
    """Tests for user-related database operations."""

    def test_add_new_user(self, temp_db, sample_user_id):
        """Should return True for new user."""
        result = db.add_user(sample_user_id)
        assert result is True

    def test_add_existing_user(self, temp_db, sample_user_id):
        """Should return False for existing user."""
        db.add_user(sample_user_id)
        result = db.add_user(sample_user_id)
        assert result is False

    def test_is_google_connected_false(self, temp_db, sample_user_id):
        """Should return False when user has no Google connection."""
        db.add_user(sample_user_id)
        assert db.is_google_connected(sample_user_id) is False

    def test_is_google_connected_true(self, temp_db, sample_user_id):
        """Should return True when user has Google tokens."""
        db.add_user(sample_user_id)
        db.store_google_tokens(
            user_id=sample_user_id,
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expiry=datetime.now() + timedelta(hours=1),
            calendar_id="primary"
        )
        assert db.is_google_connected(sample_user_id) is True

    def test_disconnect_google(self, temp_db, sample_user_id):
        """Should remove Google tokens."""
        db.add_user(sample_user_id)
        db.store_google_tokens(
            user_id=sample_user_id,
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expiry=datetime.now() + timedelta(hours=1)
        )
        db.disconnect_google(sample_user_id)
        assert db.is_google_connected(sample_user_id) is False


class TestEventOperations:
    """Tests for event-related database operations."""

    def test_store_event(self, temp_db, sample_user_id):
        """Should store event and return ID."""
        db.add_user(sample_user_id)
        event_id = db.store_event(
            user_id=sample_user_id,
            event_id="google_event_123",
            idea="Test idea",
            scheduled_time=datetime.now() + timedelta(days=1)
        )
        assert event_id > 0

    def test_get_pending_events(self, temp_db, sample_user_id):
        """Should return pending events for user."""
        db.add_user(sample_user_id)
        db.store_event(
            user_id=sample_user_id,
            event_id="event_1",
            idea="First idea",
            scheduled_time=datetime.now() + timedelta(days=1)
        )
        db.store_event(
            user_id=sample_user_id,
            event_id="event_2",
            idea="Second idea",
            scheduled_time=datetime.now() + timedelta(days=2)
        )

        events = db.get_pending_events(sample_user_id)
        assert len(events) == 2
        assert events[0]['idea'] == "First idea"

    def test_get_pending_events_empty(self, temp_db, sample_user_id):
        """Should return empty list when no events."""
        db.add_user(sample_user_id)
        events = db.get_pending_events(sample_user_id)
        assert events == []

    def test_get_event_by_id(self, temp_db, sample_user_id):
        """Should return event by database ID."""
        db.add_user(sample_user_id)
        event_db_id = db.store_event(
            user_id=sample_user_id,
            event_id="google_event_123",
            idea="Test idea",
            scheduled_time=datetime.now() + timedelta(days=1)
        )

        event = db.get_event_by_id(event_db_id)
        assert event is not None
        assert event['idea'] == "Test idea"
        assert event['user_id'] == sample_user_id

    def test_get_event_by_id_not_found(self, temp_db):
        """Should return None for non-existent event."""
        event = db.get_event_by_id(99999)
        assert event is None

    def test_mark_event_complete(self, temp_db, sample_user_id):
        """Should mark event as complete."""
        db.add_user(sample_user_id)
        event_db_id = db.store_event(
            user_id=sample_user_id,
            event_id="google_event_123",
            idea="Test idea",
            scheduled_time=datetime.now() + timedelta(days=1)
        )

        result = db.mark_event_complete(event_db_id)
        assert result is True

        # Verify event is no longer pending
        events = db.get_pending_events(sample_user_id)
        assert len(events) == 0

    def test_mark_event_complete_not_found(self, temp_db):
        """Should return False for non-existent event."""
        result = db.mark_event_complete(99999)
        assert result is False


class TestCompletionStats:
    """Tests for completion statistics."""

    def test_stats_no_events(self, temp_db, sample_user_id):
        """Should return zero stats when no events."""
        db.add_user(sample_user_id)
        stats = db.get_completion_stats(sample_user_id)

        assert stats['total'] == 0
        assert stats['completed'] == 0
        assert stats['rate'] == 0

    def test_stats_with_events(self, temp_db, sample_user_id):
        """Should calculate correct completion rate."""
        db.add_user(sample_user_id)

        # Create 3 events
        for i in range(3):
            db.store_event(
                user_id=sample_user_id,
                event_id=f"event_{i}",
                idea=f"Idea {i}",
                scheduled_time=datetime.now() + timedelta(days=i)
            )

        # Complete 2 events
        db.mark_event_complete(1)
        db.mark_event_complete(2)

        stats = db.get_completion_stats(sample_user_id)
        assert stats['total'] == 3
        assert stats['completed'] == 2
        assert abs(stats['rate'] - 66.67) < 1  # ~66.67%


class TestOAuthState:
    """Tests for OAuth state management."""

    def test_store_and_verify_oauth_state(self, temp_db, sample_user_id):
        """Should store and verify OAuth state."""
        db.add_user(sample_user_id)
        state = "test_state_12345"

        db.store_oauth_state(sample_user_id, state)
        assert db.verify_oauth_state(sample_user_id, state) is True

    def test_verify_wrong_state(self, temp_db, sample_user_id):
        """Should reject wrong OAuth state."""
        db.add_user(sample_user_id)
        db.store_oauth_state(sample_user_id, "correct_state")

        assert db.verify_oauth_state(sample_user_id, "wrong_state") is False

    def test_verify_state_no_user(self, temp_db):
        """Should return falsy value for non-existent user."""
        assert not db.verify_oauth_state(99999, "any_state")


class TestGoogleTokens:
    """Tests for Google token storage."""

    def test_store_and_get_tokens(self, temp_db, sample_user_id):
        """Should store and retrieve Google tokens."""
        db.add_user(sample_user_id)
        expiry = datetime.now() + timedelta(hours=1)

        db.store_google_tokens(
            user_id=sample_user_id,
            access_token="access_123",
            refresh_token="refresh_456",
            expiry=expiry,
            calendar_id="test_calendar"
        )

        tokens = db.get_google_tokens(sample_user_id)
        assert tokens is not None
        assert tokens['google_access_token'] == "access_123"
        assert tokens['google_refresh_token'] == "refresh_456"
        assert tokens['google_calendar_id'] == "test_calendar"

    def test_get_tokens_not_connected(self, temp_db, sample_user_id):
        """Should return None when not connected."""
        db.add_user(sample_user_id)
        tokens = db.get_google_tokens(sample_user_id)
        assert tokens is None

    def test_update_access_token(self, temp_db, sample_user_id):
        """Should update access token."""
        db.add_user(sample_user_id)
        db.store_google_tokens(
            user_id=sample_user_id,
            access_token="old_access",
            refresh_token="refresh_456",
            expiry=datetime.now() + timedelta(hours=1)
        )

        new_expiry = datetime.now() + timedelta(hours=2)
        db.update_access_token(sample_user_id, "new_access", new_expiry)

        tokens = db.get_google_tokens(sample_user_id)
        assert tokens['google_access_token'] == "new_access"


class TestTimezone:
    """Tests for timezone management."""

    def test_get_default_timezone(self, temp_db, sample_user_id):
        """Should return default timezone for new user."""
        db.add_user(sample_user_id)
        tz = db.get_user_timezone(sample_user_id)
        assert tz == db.DEFAULT_TIMEZONE

    def test_set_and_get_timezone(self, temp_db, sample_user_id):
        """Should store and retrieve user timezone."""
        db.add_user(sample_user_id)
        db.set_user_timezone(sample_user_id, "America/New_York")

        tz = db.get_user_timezone(sample_user_id)
        assert tz == "America/New_York"

    def test_set_timezone_returns_true(self, temp_db, sample_user_id):
        """Should return True when timezone is set."""
        db.add_user(sample_user_id)
        result = db.set_user_timezone(sample_user_id, "Europe/London")
        assert result is True

    def test_set_timezone_nonexistent_user(self, temp_db):
        """Should return False for non-existent user."""
        result = db.set_user_timezone(99999, "Europe/London")
        assert result is False

    def test_get_timezone_nonexistent_user(self, temp_db):
        """Should return default timezone for non-existent user."""
        tz = db.get_user_timezone(99999)
        assert tz == db.DEFAULT_TIMEZONE
