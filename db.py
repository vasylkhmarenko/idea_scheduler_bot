"""SQLite database operations for IdeaScheduler Bot."""

import os
import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager

DATABASE_PATH = os.getenv('DATABASE_PATH', 'idea_scheduler.db')


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id TEXT NOT NULL,
                idea TEXT NOT NULL,
                scheduled_time TIMESTAMP NOT NULL,
                completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()

    # Run migrations for OAuth columns
    _migrate_add_oauth_columns()


def _migrate_add_oauth_columns():
    """Add OAuth columns to existing users table."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'google_refresh_token' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN google_refresh_token TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN google_access_token TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN google_token_expiry TIMESTAMP")
            cursor.execute("ALTER TABLE users ADD COLUMN google_calendar_id TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN google_connected_at TIMESTAMP")
            cursor.execute("ALTER TABLE users ADD COLUMN oauth_state TEXT")
            conn.commit()


def add_user(user_id: int) -> bool:
    """Store new user. Returns True if new user, False if already exists."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (user_id) VALUES (?)",
                (user_id,)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def user_exists(user_id: int) -> bool:
    """Check if user exists in database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None


def store_event(user_id: int, event_id: str, idea: str, scheduled_time: datetime) -> int:
    """Save event for tracking. Returns event database ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO events (user_id, event_id, idea, scheduled_time)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, event_id, idea, scheduled_time)
        )
        conn.commit()
        return cursor.lastrowid


def get_pending_events(user_id: int) -> list:
    """Get all incomplete events for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, event_id, idea, scheduled_time
            FROM events
            WHERE user_id = ? AND completed = 0
            ORDER BY scheduled_time ASC
            """,
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_pending_events_for_date(target_date: datetime) -> list:
    """Get all incomplete events scheduled for a specific date (all users)."""
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT e.id, e.user_id, e.event_id, e.idea, e.scheduled_time
            FROM events e
            WHERE e.completed = 0
            AND e.scheduled_time >= ? AND e.scheduled_time < ?
            ORDER BY e.scheduled_time ASC
            """,
            (start_of_day, end_of_day)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_all_pending_events_by_user() -> dict:
    """Get all pending events grouped by user_id for daily reminders."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, id, event_id, idea, scheduled_time
            FROM events
            WHERE completed = 0
            AND scheduled_time <= datetime('now')
            ORDER BY user_id, scheduled_time ASC
            """
        )

        events_by_user = {}
        for row in cursor.fetchall():
            row_dict = dict(row)
            user_id = row_dict['user_id']
            if user_id not in events_by_user:
                events_by_user[user_id] = []
            events_by_user[user_id].append(row_dict)

        return events_by_user


def mark_event_complete(event_db_id: int) -> bool:
    """Mark event as done by database ID. Returns True if updated."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE events SET completed = 1 WHERE id = ?",
            (event_db_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_event_by_id(event_db_id: int) -> dict | None:
    """Get event by database ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM events WHERE id = ?",
            (event_db_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_completion_stats(user_id: int, weeks: int = 1) -> dict:
    """Get completion rate for the past N weeks."""
    start_date = datetime.now() - timedelta(weeks=weeks)

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
            FROM events
            WHERE user_id = ? AND created_at >= ?
            """,
            (user_id, start_date)
        )

        row = cursor.fetchone()
        total = row['total'] or 0
        completed = row['completed'] or 0

        return {
            'total': total,
            'completed': completed,
            'rate': (completed / total * 100) if total > 0 else 0
        }


# OAuth Token Management

def store_oauth_state(user_id: int, state: str) -> None:
    """Store OAuth state for CSRF verification."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET oauth_state = ? WHERE user_id = ?",
            (state, user_id)
        )
        conn.commit()


def verify_oauth_state(user_id: int, state: str) -> bool:
    """Verify OAuth state matches stored value."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT oauth_state FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        return row and row['oauth_state'] == state


def store_google_tokens(user_id: int, access_token: str, refresh_token: str,
                        expiry: datetime, calendar_id: str = None) -> None:
    """Store Google OAuth tokens for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET google_access_token = ?,
                google_refresh_token = ?,
                google_token_expiry = ?,
                google_calendar_id = ?,
                google_connected_at = CURRENT_TIMESTAMP,
                oauth_state = NULL
            WHERE user_id = ?
            """,
            (access_token, refresh_token, expiry, calendar_id or 'primary', user_id)
        )
        conn.commit()


def get_google_tokens(user_id: int) -> dict | None:
    """Get stored Google tokens for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT google_access_token, google_refresh_token,
                   google_token_expiry, google_calendar_id
            FROM users WHERE user_id = ?
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        if row and row['google_refresh_token']:
            return dict(row)
        return None


def update_access_token(user_id: int, access_token: str, expiry: datetime) -> None:
    """Update access token after refresh."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET google_access_token = ?, google_token_expiry = ?
            WHERE user_id = ?
            """,
            (access_token, expiry, user_id)
        )
        conn.commit()


def is_google_connected(user_id: int) -> bool:
    """Check if user has connected Google Calendar."""
    tokens = get_google_tokens(user_id)
    return tokens is not None


def disconnect_google(user_id: int) -> None:
    """Remove Google OAuth tokens (disconnect)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET google_access_token = NULL,
                google_refresh_token = NULL,
                google_token_expiry = NULL,
                google_calendar_id = NULL,
                google_connected_at = NULL
            WHERE user_id = ?
            """,
            (user_id,)
        )
        conn.commit()
