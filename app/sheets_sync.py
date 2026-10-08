import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")


def get_sheet():
    """Get the Google Sheet object (first worksheet)."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        SERVICE_ACCOUNT_FILE, scope
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    return sheet


def sync_scan_to_sheet(student_email: str, student_roll: str, event_id: int, check_in_time: str):
    """
    Update the attendee's row in Google Sheets with Present status.
    Finds the row matching email + roll, then updates Status and Timestamp columns.
    """
    try:
        sheet = get_sheet()
        worksheet = sheet.get_worksheet(0)

        all_rows = worksheet.get_all_values()
        if len(all_rows) <= 1:
            return {"status": "no_data"}

        # Find the row matching email + roll
        header = all_rows[0]
        target_row = None
        for idx, row in enumerate(all_rows[1:], start=2):
            if len(row) < 4:
                continue
            if row[2].strip().lower() == student_email.lower() and \
               row[3].strip().upper() == student_roll.upper():
                target_row = idx
                break

        if target_row is None:
            return {"status": "not_found", "email": student_email}

        # Check if Status/Check-in columns exist in header
        # If not, add them
        if "Status" not in header:
            next_col = len(header) + 1
            worksheet.update_cell(1, next_col, "Status")
            worksheet.update_cell(1, next_col + 1, "Check-In Time")
            header.extend(["Status", "Check-In Time"])

        status_col = header.index("Status") + 1
        time_col = header.index("Check-In Time") + 1

        worksheet.update_cell(target_row, status_col, "Present")
        worksheet.update_cell(target_row, time_col, check_in_time)

        return {"status": "updated", "row": target_row}

    except Exception as e:
        print(f"❌ Sheets sync error: {str(e)}")
        return {"status": "error", "message": str(e)}