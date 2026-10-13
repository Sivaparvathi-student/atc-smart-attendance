import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
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


def get_sheet(sheet_id: str = None):
    """Get the Google Sheet object (first worksheet)."""
    target_id = sheet_id or DEFAULT_SHEET_ID
    if not target_id:
        raise ValueError("No Google Sheet ID provided or configured.")
    creds = get_service_account_credentials()
    client = gspread.authorize(creds)
    sheet = client.open_by_key(target_id)
    return sheet


def sync_scan_to_sheet(student_email: str, student_roll: str, event_id: int, check_in_time: str, sheet_id: str = None):
    """
    Update attendee's row in Google Sheets with Present status and timestamp.
    Dynamically finds email, roll, status, and check-in time columns.
    """
    try:
        sheet = get_sheet(sheet_id)
        worksheet = sheet.get_worksheet(0)

        all_rows = worksheet.get_all_values()
        if len(all_rows) <= 1:
            return {"status": "no_data"}

        raw_headers = all_rows[0]
        headers_norm = [h.strip().lower().replace(" ", "_").replace(".", "") for h in raw_headers]

        def find_col_idx(*names):
            for n in names:
                n_norm = n.lower().replace(" ", "_").replace(".", "")
                if n_norm in headers_norm:
                    return headers_norm.index(n_norm)
            return None

        email_col_idx = find_col_idx(
            "email", "email_address", "email_id", "student_email",
            "mail", "e_mail", "emailid"
        )
        roll_col_idx = find_col_idx(
            "roll_number", "roll_no", "roll", "rollnumber",
            "student_roll_number", "registration_number",
            "regd_no", "admission_no", "student_id"
        )

        # Fallbacks if headers cannot be determined by name
        if email_col_idx is None and len(raw_headers) > 2:
            email_col_idx = 2
        if roll_col_idx is None and len(raw_headers) > 3:
            roll_col_idx = 3

        if email_col_idx is None or roll_col_idx is None:
            return {"status": "error", "message": "Could not identify Email or Roll Number columns"}

        # Find the row matching email and roll
        target_row = None
        email_clean = student_email.strip().lower()
        roll_clean = student_roll.strip().upper()

        for idx, row in enumerate(all_rows[1:], start=2):
            r_email = row[email_col_idx].strip().lower() if email_col_idx < len(row) else ""
            r_roll = row[roll_col_idx].strip().upper() if roll_col_idx < len(row) else ""
            if r_email == email_clean and r_roll == roll_clean:
                target_row = idx
                break

        # Fallback: match by email alone
        if target_row is None:
            for idx, row in enumerate(all_rows[1:], start=2):
                r_email = row[email_col_idx].strip().lower() if email_col_idx < len(row) else ""
                if r_email == email_clean:
                    target_row = idx
                    break

        if target_row is None:
            return {"status": "not_found", "email": student_email}

        # Find or create Status and Check-In Time columns
        status_col_idx = find_col_idx("status", "attendance_status")
        time_col_idx = find_col_idx("check_in_time", "checkin_time", "scan_time", "check_in")

        if status_col_idx is None:
            status_col_idx = len(raw_headers)
            raw_headers.append("Status")
            headers_norm.append("status")
            worksheet.update_cell(1, status_col_idx + 1, "Status")

        if time_col_idx is None:
            time_col_idx = len(raw_headers)
            raw_headers.append("Check-In Time")
            headers_norm.append("check_in_time")
            worksheet.update_cell(1, time_col_idx + 1, "Check-In Time")

        worksheet.update_cell(target_row, status_col_idx + 1, "Present")
        worksheet.update_cell(target_row, time_col_idx + 1, check_in_time)

        return {"status": "updated", "row": target_row}

    except Exception as e:
        print(f"❌ Sheets sync error: {str(e)}")
        return {"status": "error", "message": str(e)}