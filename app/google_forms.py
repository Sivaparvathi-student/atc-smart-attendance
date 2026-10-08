import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")


def get_sheet_client():
    """Authenticate with Google Sheets API using service account."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        SERVICE_ACCOUNT_FILE, scope
    )
    client = gspread.authorize(creds)
    return client


def fetch_new_registrations(worksheet_index=0):
    """
    Fetch all rows from the Google Form response sheet.
    Column order (from Google Forms): Timestamp, Name, Email, Roll Number
    """
    client = get_sheet_client()
    sheet = client.open_by_key(SHEET_ID)
    worksheet = sheet.get_worksheet(worksheet_index)
    
    # Get all values as list of lists
    all_rows = worksheet.get_all_values()
    
    if len(all_rows) <= 1:
        return []  # Only header, no data
    
    header = all_rows[0]  # ["Timestamp", "Name", "Email", "Roll Number"]
    data_rows = all_rows[1:]  # Skip header
    
    registrations = []
    for idx, row in enumerate(data_rows, start=2):  # Row 2 is first data row
        if len(row) < 4:
            continue  # Skip incomplete rows
        registrations.append({
            "row_number": idx,
            "timestamp": row[0],
            "student_name": row[1],
            "student_email": row[2].strip().lower(),
            "student_roll_number": row[3].strip().upper()
        })
    return registrations