"""Google Calendar API wrapper for IdeaScheduler Bot."""

import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
DEFAULT_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'vkhmarenko@gmail.com')
DEFAULT_TIMEZONE = os.getenv('TIMEZONE', 'Europe/Kyiv')


def load_credentials(json_path: str = None):
    """Load Google credentials from JSON file."""
    path = json_path or os.getenv('GOOGLE_CREDENTIALS_PATH', 'google_creds.json')
    return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)


def get_calendar_service(credentials):
    """Build Calendar API service."""
    return build('calendar', 'v3', credentials=credentials)


def create_event(credentials, idea: str, datetime_obj: datetime,
                 calendar_id: str = None, timezone: str = None) -> str:
    """Create Google Calendar event. Returns event_id."""
    calendar_id = calendar_id or DEFAULT_CALENDAR_ID
    timezone = timezone or DEFAULT_TIMEZONE
    service = get_calendar_service(credentials)

    end_time = datetime_obj + timedelta(hours=1)

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


def get_events_for_date(credentials, date: datetime,
                        calendar_id: str = None) -> list:
    """Get all events for a specific date."""
    calendar_id = calendar_id or DEFAULT_CALENDAR_ID
    service = get_calendar_service(credentials)

    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start.isoformat() + 'Z',
        timeMax=end.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return events_result.get('items', [])


def update_event_completion(credentials, event_id: str, completed: bool = True,
                           calendar_id: str = None) -> bool:
    """Mark event as completed by updating description."""
    calendar_id = calendar_id or DEFAULT_CALENDAR_ID
    service = get_calendar_service(credentials)

    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    status = "Completed" if completed else "Pending"
    event['description'] = f"{status} - Created by IdeaScheduler Bot"

    service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
    return True
