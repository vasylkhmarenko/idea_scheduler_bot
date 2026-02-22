"""Google Calendar API wrapper for IdeaScheduler Bot."""

import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build

DEFAULT_TIMEZONE = os.getenv('TIMEZONE', 'Europe/Kyiv')


def _get_calendar_service(credentials):
    """Build Calendar API service."""
    return build('calendar', 'v3', credentials=credentials)

def create_event_for_user(user_id: int, idea: str, datetime_obj: datetime,
                          timezone: str = None, duration_minutes: int = 60) -> str | None:
    """
    Create Google Calendar event for a specific user using their OAuth credentials.
    Returns event_id or None if user not connected.

    Args:
        duration_minutes: Event duration in minutes (default: 60, range: 15-480)
    """
    import oauth
    import db

    credentials = oauth.get_user_credentials(user_id)
    if not credentials:
        return None

    tokens = db.get_google_tokens(user_id)
    calendar_id = tokens.get('google_calendar_id') or 'primary'
    timezone = timezone or DEFAULT_TIMEZONE

    # Clamp duration to reasonable range (15 min to 8 hours)
    duration_minutes = max(15, min(480, duration_minutes))

    service = _get_calendar_service(credentials)
    end_time = datetime_obj + timedelta(minutes=duration_minutes)

    event = {
        'summary': idea,
        'start': {
            'dateTime': datetime_obj.isoformat(),
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': timezone,
        },
        'description': 'Created by IdeaScheduler Bot',
    }

    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    return created_event['id']


def update_event_completion_for_user(user_id: int, event_id: str,
                                     completed: bool = True) -> bool:
    """Mark event as completed for a specific user using their OAuth credentials."""
    import oauth
    import db

    credentials = oauth.get_user_credentials(user_id)
    if not credentials:
        return False

    tokens = db.get_google_tokens(user_id)
    calendar_id = tokens.get('google_calendar_id') or 'primary'

    service = _get_calendar_service(credentials)

    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        status = "Completed" if completed else "Pending"
        event['description'] = f"{status} - Created by IdeaScheduler Bot"
        service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        return True
    except Exception:
        return False
