from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheets_service():
    creds = Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def get_new_applications():
    """
    Reads Form Responses sheet.
    Returns rows where column 'Status' is empty (not yet processed).
    Assumes the last column is 'Status' — added manually once to the sheet header.
    """
    service = get_sheets_service()
    sheet = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=config.SPREADSHEET_ID,
        range=config.RESPONSES_SHEET
    ).execute()

    rows = result.get("values", [])
    if not rows:
        return []

    headers = rows[0]
    data_rows = rows[1:]

    # Ensure Status column exists in header
    if "Status" not in headers:
        raise ValueError(
            "Please add a 'Status' column as the last column in your Form Responses sheet header."
        )

    status_col_index = headers.index("Status")

    new_applications = []
    for i, row in enumerate(data_rows):
        # Pad row to match header length
        while len(row) < len(headers):
            row.append("")

        status = row[status_col_index].strip()
        if status == "":
            entry = dict(zip(headers, row))
            entry["_row_index"] = i + 2  # 1-indexed, +1 for header
            new_applications.append(entry)

    return new_applications


def check_committee_availability(committee_name):
    """
    Checks the Committee Availability sheet for remaining spots.
    Sheet format: Column A = Committee Name, Column B = Spots Remaining
    """
    service = get_sheets_service()
    sheet = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=config.SPREADSHEET_ID,
        range=config.AVAILABILITY_SHEET
    ).execute()

    rows = result.get("values", [])
    for row in rows[1:]:  # skip header
        if len(row) >= 2 and row[0].strip().lower() == committee_name.strip().lower():
            spots = int(row[1]) if row[1].isdigit() else 0
            return spots > 0
    return False


def mark_as_processed(row_index, status="INVOICE_SENT"):
    """
    Writes status into the Status column for a given row.
    row_index is 1-based (Google Sheets row number).
    """
    service = get_sheets_service()
    sheet = service.spreadsheets()

    # Find the column letter for Status
    result = sheet.values().get(
        spreadsheetId=config.SPREADSHEET_ID,
        range=f"{config.RESPONSES_SHEET}!1:1"
    ).execute()

    headers = result.get("values", [[]])[0]
    if "Status" not in headers:
        raise ValueError("Status column not found in sheet header.")

    col_index = headers.index("Status")
    # Convert column index to letter(s) - handles columns beyond Z
    def col_index_to_letter(index):
        letter = ""
        while index >= 0:
            letter = chr(index % 26 + ord("A")) + letter
            index = index // 26 - 1
        return letter

    col_letter = col_index_to_letter(col_index)
    cell = f"{config.RESPONSES_SHEET}!{col_letter}{row_index}"

    sheet.values().update(
        spreadsheetId=config.SPREADSHEET_ID,
        range=cell,
        valueInputOption="RAW",
        body={"values": [[status]]}
    ).execute()

    print(f"Row {row_index} marked as {status}")
