import os
from dotenv import load_dotenv

load_dotenv()

# Google
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")          # ID from the Google Sheet URL
RESPONSES_SHEET = os.getenv("RESPONSES_SHEET", "Form Responses 1")
AVAILABILITY_SHEET = os.getenv("AVAILABILITY_SHEET", "Committee Availability")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# Gmail
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "externalaffairs.numun.jp@gmail.com")

# Discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

# Paths
PDF_OUTPUT_DIR = os.getenv("PDF_OUTPUT_DIR", "invoices")
PENDING_FILE = "pending.json"
