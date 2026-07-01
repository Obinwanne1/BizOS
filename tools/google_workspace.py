import json
import os
import base64
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar.readonly",
]

_BASE = Path(__file__).parent.parent
TOKEN_PATH = _BASE / "data" / "google_token.json"
CREDS_PATH = _BASE / "data" / "google_credentials.json"


def _get_creds():
    if not GOOGLE_AVAILABLE:
        return None
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            try:
                creds = flow.run_local_server(port=0)
            except Exception:
                # Headless fallback — print URL, return None to avoid hanging
                auth_url, _ = flow.authorization_url(prompt="consent")
                print(f"\n[Google Auth] Open this URL to authorize:\n{auth_url}\n")
                print("After authorizing, save the token manually via scripts/google_auth.py")
                return None
        with open(str(TOKEN_PATH), "w", encoding="utf-8") as f:
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
        return {
            "events": [
                {"summary": "Product Review", "start": "10:00 AM"},
                {"summary": "Investor Call", "start": "2:00 PM"},
            ],
            "stub": True,
        }

    try:
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


def write_to_sheets(title: str, data: dict) -> dict:
    """Write structured data to a new Google Sheet. Stubs if not authenticated."""
    creds = _get_creds()
    if not creds:
        print(f"[Sheets stub] Would write '{title}' to Google Sheets")
        return {"stub": True, "title": title}

    try:
        service = build("sheets", "v4", credentials=creds)
        sheet_title = f"{title} — {datetime.now().strftime('%Y-%m-%d')}"
        spreadsheet = service.spreadsheets().create(
            body={"properties": {"title": sheet_title}, "sheets": [{"properties": {"title": "Data"}}]},
            fields="spreadsheetId,spreadsheetUrl",
        ).execute()
        sheet_id = spreadsheet["spreadsheetId"]

        rows = [["Key", "Value"]]
        for k, v in data.items():
            rows.append([str(k), json.dumps(v) if isinstance(v, (dict, list)) else str(v)])

        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range="Data!A1",
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()

        return {"sheet_id": sheet_id, "url": spreadsheet.get("spreadsheetUrl", ""), "title": sheet_title}
    except Exception as e:
        return {"error": str(e)}


def upload_to_drive(filename: str, data: dict) -> dict:
    """Upload a JSON file to Google Drive. Stubs if not authenticated."""
    creds = _get_creds()
    if not creds:
        print(f"[Drive stub] Would upload '{filename}' to Google Drive")
        return {"stub": True, "filename": filename}

    try:
        service = build("drive", "v3", credentials=creds)
        content = json.dumps(data, indent=2).encode("utf-8")
        media = MediaInMemoryUpload(content, mimetype="application/json", resumable=False)
        file_metadata = {"name": filename, "mimeType": "application/json"}
        file = service.files().create(body=file_metadata, media_body=media, fields="id,webViewLink").execute()
        return {"file_id": file["id"], "url": file.get("webViewLink", "")}
    except Exception as e:
        return {"error": str(e)}
