import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuthCredentials
import config

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = OAuthCredentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open("token.json", "w") as f:
                f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def format_english_date(date_str):
    """Convert '2026-05-14' to 'May 14th, 2026'"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day = dt.day
    if 11 <= day <= 13:
        suffix = "th"
    elif day % 10 == 1:
        suffix = "st"
    elif day % 10 == 2:
        suffix = "nd"
    elif day % 10 == 3:
        suffix = "rd"
    else:
        suffix = "th"
    return dt.strftime(f"%B {day}{suffix}, %Y")


def format_japanese_date(date_str):
    """Convert '2026-05-14' to '2026年5月14日'"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.year}年{dt.month}月{dt.day}日"


def send_invoice_email(to_email, full_name, full_name_ja, deadline_str, pdf_path):
    service = get_gmail_service()

    en_deadline = format_english_date(deadline_str)
    ja_deadline = format_japanese_date(deadline_str)

    msg = MIMEMultipart()
    msg["From"] = config.SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = "NUMUN 2026 – Invoice & Payment Details | 請求書・お支払いについて"

    body = f"""Dear {full_name},

Thank you for registering for Nagoya University Model United Nations 2026! We have successfully received your application.

To finalize your submission, please complete the payment process as written in the invoice attached to this email. Your payment is due on {en_deadline} 23:59 JST and be sure to write your full name as the sender.

Please also take a moment to review our refund policies, which are included in the attachment.

Once payment is processed, your spot will be officially secured. We look forward to seeing you at the conference!

Best regards,
External Affairs Team
NUMUN 2026

――――――――――――――――――――――――――――――――

{full_name_ja}様、

この度はNagoya University Model United Nations 2026にご登録いただき、誠にありがとうございます。お申し込みを正常に受け付けいたしました。

お申し込みを確定するため、添付のインボイスに記載された方法にてお支払いをお願いいたします。お支払い期限は{ja_deadline} 23:59 JSTとなっております。お振込みの際は、必ずお名前（フルネーム）を送金者名としてご記入ください。

また、添付ファイルに返金ポリシーも記載しておりますので、ご一読いただけますようお願いいたします。

お支払いが確認され次第、ご参加が正式に確定いたします。会議にてお会いできることを楽しみにしております。

敬具
渉外チーム
NUMUN 2026
"""

    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Attach PDF with clean ASCII filename
    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", 'attachment; filename="NUMUN2026_Invoice.pdf"')
    msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(
        userId="me",
        body={"raw": raw}
    ).execute()

    print(f"Email sent to {to_email}")