"""Shared test fixtures."""

import os
import sys
import tempfile
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables before importing modules
os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_12345'
os.environ['GOOGLE_CLIENT_SECRETS_PATH'] = 'test_secrets.json'


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    import db

    # Create temp file for test database
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Override database path
    original_path = db.DATABASE_PATH
    db.DATABASE_PATH = path

    # Initialize database
    db.init_db()

    yield path

    # Cleanup
    db.DATABASE_PATH = original_path
    os.unlink(path)


@pytest.fixture
def sample_user_id():
    """Sample Telegram user ID for testing."""
    return 123456789
