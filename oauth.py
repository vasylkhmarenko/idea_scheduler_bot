"""Google OAuth 2.0 handler for per-user Calendar authentication."""

import os
import json
import logging
import secrets
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

import db

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']
CLIENT_SECRETS_FILE = os.getenv('GOOGLE_CLIENT_SECRETS_PATH', 'client_secrets.json')
REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', 'https://vasylkhmarenko.pythonanywhere.com/oauth/callback')

# Cache client credentials at module load to avoid file I/O per request
_CLIENT_ID = None
_CLIENT_SECRET = None


def generate_oauth_state(user_id: int) -> str:
    """Generate and store a random state for CSRF protection."""
    state = f"{user_id}:{secrets.token_urlsafe(32)}"
    db.store_oauth_state(user_id, state)
    return state


def parse_oauth_state(state: str) -> tuple[int, str] | None:
    """Parse state string to extract user_id and token."""
    if not state:
        return None
    try:
        parts = state.split(':', 1)
        if len(parts) == 2:
            return int(parts[0]), parts[1]
    except (ValueError, TypeError):
        pass
    return None


def get_authorization_url(user_id: int) -> str:
    """Generate Google OAuth authorization URL for a user."""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    state = generate_oauth_state(user_id)

    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=state
    )

    return authorization_url


def exchange_code_for_tokens(code: str, state: str) -> tuple[int, bool, str]:
    """
    Exchange authorization code for tokens.
    Returns: (user_id, success, message)
    """
    parsed = parse_oauth_state(state)
    if not parsed:
        return 0, False, "Invalid state parameter"

    user_id, _ = parsed

    if not db.verify_oauth_state(user_id, state):
        return user_id, False, "State verification failed"

    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
            state=state
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        expiry = datetime.now() + timedelta(hours=1)

        db.store_google_tokens(
            user_id=user_id,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expiry=expiry,
            calendar_id='primary'
        )

        return user_id, True, "Successfully connected Google Calendar!"

    except Exception as e:
        logger.error(f"OAuth token exchange failed for user {user_id}: {e}")
        return user_id, False, "Failed to connect. Please try again."


def get_user_credentials(user_id: int) -> Credentials | None:
    """
    Get valid credentials for a user, refreshing if necessary.
    Returns None if user not connected or refresh fails.
    """
    tokens = db.get_google_tokens(user_id)
    if not tokens:
        return None

    client_id, client_secret = _get_client_credentials()

    credentials = Credentials(
        token=tokens['google_access_token'],
        refresh_token=tokens['google_refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )

    expiry = tokens['google_token_expiry']
    if isinstance(expiry, str):
        expiry = datetime.fromisoformat(expiry)

    if expiry and datetime.now() >= expiry - timedelta(minutes=5):
        try:
            credentials.refresh(Request())
            new_expiry = datetime.now() + timedelta(hours=1)
            db.update_access_token(user_id, credentials.token, new_expiry)
        except Exception:
            return None

    return credentials


def _get_client_credentials() -> tuple[str, str]:
    """Get client ID and secret from secrets file (cached)."""
    global _CLIENT_ID, _CLIENT_SECRET
    if _CLIENT_ID is None:
        with open(CLIENT_SECRETS_FILE) as f:
            data = json.load(f)
            _CLIENT_ID = data['web']['client_id']
            _CLIENT_SECRET = data['web']['client_secret']
    return _CLIENT_ID, _CLIENT_SECRET
