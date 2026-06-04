import io
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth.transport.requests import Request
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from datetime import datetime
import config

TEMPLATE_ID = "1G2lE7-peaKRqv8kh8_lA05FHrbUMJHPKrjFSpW6bHZ4"
REFUND_POLICY_ID = "1Gg5-px_jiiK0stJLyfh-QNBfUOmz6wOv"

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_services():
    creds = None
    if os.path.exists("token.json"):
        creds = OAuthCredentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open("token.json", "w") as f:
                f.write(creds.to_json())
    drive_service = build("drive", "v3", credentials=creds)
    docs_service = build("docs", "v1", credentials=creds)
    return drive_service, docs_service


def to_japanese_date(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.year}年{dt.month}月{dt.day}日"


def generate_invoice_pdf(full_name, full_name_ja, date_str, deadline_str, output_path):
    drive_service, docs_service = get_services()
    os.makedirs(config.PDF_OUTPUT_DIR, exist_ok=True)

    ja_date = to_japanese_date(date_str)
    ja_deadline = to_japanese_date(deadline_str)

    replacements = {
        "{{FULL_NAME}}": full_name,
        "{{FULL_NAME_JA}}": full_name_ja,
        "{{DATE}}": date_str,
        "{{DEADLINE}}": deadline_str,
        "{{日付}}": ja_date,
        "{{期限}}": ja_deadline,
    }

    # 1. Copy template
    print("Copying template...")
    copy_title = f"NUMUN2026_Invoice_{full_name.replace(' ', '_')}_TEMP"
    copied = drive_service.files().copy(
        fileId=TEMPLATE_ID,
        body={"name": copy_title}
    ).execute()
    copy_id = copied["id"]
    print(f"Copy created: {copy_id}")

    try:
        # 2. Replace placeholders
        requests = []
        for placeholder, value in replacements.items():
            requests.append({
                "replaceAllText": {
                    "containsText": {"text": placeholder, "matchCase": True},
                    "replaceText": value
                }
            })
        docs_service.documents().batchUpdate(
            documentId=copy_id,
            body={"requests": requests}
        ).execute()
        print(f"Placeholders replaced for {full_name}")

        # 3. Export as PDF
        print("Exporting PDF...")
        invoice_only_path = output_path.replace(".pdf", "_invoice_only.pdf")
        request = drive_service.files().export_media(
            fileId=copy_id,
            mimeType="application/pdf"
        )
        pdf_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(pdf_buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        with open(invoice_only_path, "wb") as f:
            f.write(pdf_buffer.getvalue())
        print(f"Invoice PDF exported: {invoice_only_path}")

        # 4. Remove Tab 1 first page
        reader = PdfReader(invoice_only_path)
        writer = PdfWriter()
        for page in reader.pages[1:]:
            writer.add_page(page)
        with open(invoice_only_path, "wb") as f:
            writer.write(f)
        print("Tab 1 page removed")

    finally:
        # 5. Always delete the copy
        drive_service.files().delete(fileId=copy_id).execute()
        print("Temp copy deleted")

    # 6. Download refund policy
    print("Downloading refund policy...")
    refund_path = os.path.join(config.PDF_OUTPUT_DIR, "refund_policy.pdf")
    request = drive_service.files().get_media(fileId=REFUND_POLICY_ID)
    refund_buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(refund_buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    with open(refund_path, "wb") as f:
        f.write(refund_buffer.getvalue())

    # 7. Merge invoice + refund policy
    merger = PdfMerger()
    merger.append(invoice_only_path)
    merger.append(refund_path)
    merger.write(output_path)
    merger.close()
    os.remove(invoice_only_path)
    print(f"Final merged PDF: {output_path}")

    return output_path