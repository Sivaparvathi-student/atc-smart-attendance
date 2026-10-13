import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")


def get_service_account_path():
    cred_file = SERVICE_ACCOUNT_FILE
    if not os.path.isabs(cred_file):
        if not os.path.exists(cred_file):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cand = os.path.join(base_dir, SERVICE_ACCOUNT_FILE)
            if os.path.exists(cand):
                return cand
    return cred_file


def get_service_account_credentials():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    cred_path = get_service_account_path()
    return ServiceAccountCredentials.from_json_keyfile_name(
        cred_path, scope
    )


def get_service_account_email():
    try:
        creds = get_service_account_credentials()
        return creds.service_account_email
    except Exception:
        return "attendance-bot@atc-attendence-510814.iam.gserviceaccount.com"


def get_sheet_client():
    """Authenticate with Google Sheets API."""
    creds = get_service_account_credentials()
    client = gspread.authorize(creds)
    return client


import re
import requests


def clean_sheet_id(raw_input: str) -> str:
    """Extract clean 44-char ID if user pasted full URL or has extra whitespace/slashes."""
    if not raw_input:
        return ""
    s = raw_input.strip()
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", s)
    if m:
        return m.group(1)
    return s


def get_drive_file_info(file_id: str) -> dict | None:
    """Query Google Drive API to check the file's name and mimeType."""
    try:
        creds = get_service_account_credentials()
        token = creds.get_access_token().access_token
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=id,name,mimeType"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None


def fetch_new_registrations(sheet_id: str, worksheet_index: int = 0):
    """
    Fetch registrations from Google Sheet dynamically.

    - Required headers: Name, Email, Roll Number (with flexible variations)
    - Order of columns DOES NOT matter — reads by header name
    - All extra columns go into 'extra_data' as JSON

    Accepts multiple header variations:
    - Name: Name, Full Name, Student Name, Your Name
    - Email: Email, Email Address, Email ID, Mail, Student Email
    - Roll: Roll Number, Roll No, Roll, Regd No, Admission No, Registration Number
    """
    clean_id = clean_sheet_id(sheet_id)
    client = get_sheet_client()
    try:
        sheet = client.open_by_key(clean_id)
    except gspread.exceptions.SpreadsheetNotFound:
        bot_email = get_service_account_email()
        drive_info = get_drive_file_info(clean_id)
        if drive_info and drive_info.get("mimeType") == "application/vnd.google-apps.form":
            form_name = drive_info.get("name", "Google Form")
            raise ValueError(
                f"⚠️ The ID '{clean_id}' belongs to a Google Form ('{form_name}'), NOT a Google Sheet!\n\n"
                f"Google Sheets API cannot read directly from a Form editor.\n\n"
                f"👉 How to fix:\n"
                f"1. Open your Google Form '{form_name}' in browser.\n"
                f"2. Click the 'Responses' tab at the top.\n"
                f"3. Click the green 'Link to Sheets' (or 'View in Sheets') icon to open the spreadsheet.\n"
                f"4. In that Google Sheet, click the 'Share' button (top right) and add:\n"
                f"   {bot_email} (with Editor permission).\n"
                f"5. Copy the Sheet ID from that spreadsheet's URL and update your event."
            )
        raise ValueError(
            f"Google Sheet '{clean_id}' was not found or is not shared with the attendance bot. "
            f"Please open the Google Sheet (Responses spreadsheet), click 'Share', and add '{bot_email}' with Editor permission."
        )
    except Exception as e:
        raise ValueError(f"Could not open Google Sheet '{clean_id}': {str(e)}")

    worksheet = sheet.get_worksheet(worksheet_index)

    all_rows = worksheet.get_all_values()
    if len(all_rows) <= 1:
        return []

    # Normalize headers: lowercase, replace spaces with underscores
    raw_headers = all_rows[0]
    headers = [h.strip().lower().replace(" ", "_").replace(".", "") for h in raw_headers]

    def find_col(*names):
        """Find a column index by trying multiple header variations."""
        for n in names:
            n_norm = n.lower().replace(" ", "_").replace(".", "")
            if n_norm in headers:
                return headers.index(n_norm)
        return None

    # 🔽 ADD MORE VARIATIONS HERE IF NEEDED
    name_col = find_col(
        "name", "full_name", "student_name", "your_name"
    )
    email_col = find_col(
        "email", "email_address", "email_id", "student_email",
        "mail", "e_mail", "emailid"
    )
    roll_col = find_col(
        "roll_number", "roll_no", "roll", "rollnumber",
        "student_roll_number", "registration_number",
        "regd_no", "regd_number", "admission_no", "student_id"
    )

    if None in [name_col, email_col, roll_col]:
        raise ValueError(
            f"Required columns missing. "
            f"Found headers: {raw_headers}. "
            f"Every Google Form must have: Name, Email, Roll Number"
        )

    registrations = []
    for idx, row in enumerate(all_rows[1:], start=2):
        if not any(row):
            continue

        def get_val(col_idx):
            if col_idx is None or col_idx >= len(row):
                return None
            v = row[col_idx].strip() if row[col_idx] else ""
            return v if v else None

        name = get_val(name_col)
        email = get_val(email_col)
        roll = get_val(roll_col)

        # Skip incomplete rows
        if not all([name, email, roll]):
            continue

        # Collect all extra columns into JSON
        extra = {}
        for i, header in enumerate(headers):
            if i in [name_col, email_col, roll_col]:
                continue
            if header in ["timestamp", ""]:
                continue
            value = row[i].strip() if i < len(row) and row[i] else ""
            if value:
                extra[header] = value

        registrations.append({
            "row_number": idx,
            "student_name": name,
            "student_email": email.lower(),
            "student_roll_number": roll.upper(),
            "extra_data": extra if extra else None
        })

    return registrations