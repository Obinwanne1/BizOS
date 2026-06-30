import os
import base64
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar.readonly",
]

TOKEN_PATH = "data/google_token.json"
CREDS_PATH = "data/google_credentials.json"


def _get_creds():
    if not GOOGLE_AVAILABLE:
        return None
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_PATH):
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return creds


def create_gmail_draft(to: str, subject: str, body: str) -> dict:
    creds = _get_creds()
    if not creds:
        print(f"[Gmail stub] Draft to: {to} | Subject: {subject}")
        return {"stub": True, "to": to, "subject": subject}

    try:
        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return {"draft_id": draft["id"], "to": to}
    except Exception as e:
        return {"error": str(e)}


def get_calendar_today() -> dict:
    creds = _get_creds()
    if not creds:
        return {"events": [{"summary": "Product Review", "start": "10:00 AM"}, {"summary": "Investor Call", "start": "2:00 PM"}], "stub": True}

    try:
        from datetime import datetime, timezone
        service = build("calendar", "v3", credentials=creds)
        now = datetime.now(timezone.utc).isoformat()
        end = datetime.now(timezone.utc).replace(hour=23, minute=59).isoformat()
        events_result = service.events().list(
            calendarId="primary", timeMin=now, timeMax=end,
            maxResults=10, singleEvents=True, orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        return {
            "events": [
                {"summary": e.get("summary", ""), "start": e.get("start", {}).get("dateTime", "")}
                for e in events
            ]
        }
    except Exception as e:
        return {"error": str(e), "events": []}
