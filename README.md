# NUMUN 2026 Registration Automation

Automated pipeline for processing NUMUN Japan conference registrations. When a participant submits a Google Form, this system automatically generates a personalized invoice PDF, routes it through a Discord approval workflow, and delivers it to the applicant via email — with zero manual handling.

## How It Works

```
Google Form Submission
        ↓
generate_invoices.py   (runs at 23:59 daily)
  - Reads new responses from Google Sheets
  - Generates personalized invoice PDF (English + Japanese)
  - Merges invoice with refund policy into a single PDF
  - Saves to pending queue
        ↓
post_for_approval.py   (runs at 12:00 daily)
  - Posts each pending invoice to a Discord channel
  - Attaches the PDF for review
  - Waits for ✅ reaction from an EA committee member
        ↓
send_approved_emails.py   (runs at 13:00 daily)
  - Checks Discord for ✅ approvals
  - Sends invoice email to the applicant's registered address
  - Updates Google Sheets status to INVOICE_SENT
```

## Tech Stack

- **Python** — core automation logic
- **Google Sheets API** — reads form responses, tracks processing status
- **Google Docs API** — fills invoice template with applicant data
- **Google Drive API** — copies, exports, and merges PDF documents
- **Gmail API (OAuth)** — sends invoice emails
- **Discord.py** — human-in-the-loop approval via Discord reactions
- **PyPDF2** — merges invoice and refund policy into one PDF
- **Cron** — schedules the three daily jobs

## Project Structure

```
numun-automation/
├── generate_invoices.py      # Collects new applications, generates invoice PDFs
├── post_for_approval.py      # Posts invoices to Discord for EA approval
├── send_approved_emails.py   # Sends emails after Discord approval
├── invoice.py                # PDF generation logic (template fill + merge)
├── gmail_sender.py           # Email sending via Gmail OAuth
├── sheets.py                 # Google Sheets read/write helpers
├── config.py                 # Centralised config loaded from .env
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variable template (see Setup)
```

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/wennywennywen/numun-automation.git
cd numun-automation
pip install -r requirements.txt
```

### 2. Configure environment variables
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

```env
SPREADSHEET_ID=your_google_sheet_id
RESPONSES_SHEET=Form Responses 1
AVAILABILITY_SHEET=Committee Availability
GOOGLE_CREDENTIALS_FILE=service_account.json
SENDER_EMAIL=your@gmail.com
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id
PDF_OUTPUT_DIR=invoices
```

### 3. Add credentials
- `service_account.json` — Google service account key (for Sheets/Drive/Docs)
- `token.json` — OAuth token for Gmail sending (generated on first run)

### 4. Schedule with cron
```bash
crontab -e
```
```
59 23 * * * cd /path/to/numun-automation && python generate_invoices.py
0  12 * * * cd /path/to/numun-automation && python post_for_approval.py
0  13 * * * cd /path/to/numun-automation && python send_approved_emails.py
```

## Key Design Decisions

- **Human-in-the-loop approval** — invoices are never sent automatically. A Discord ✅ reaction from an EA member is required, preventing accidental sends.
- **Stateless daily runs** — `generate_invoices.py` rebuilds the pending queue fresh each night, avoiding stale state issues.
- **Dual email delivery** — sends to both the form-submitted email and the Google account email when they differ, ensuring delivery.
- **Temp file cleanup** — Google Docs copies used for PDF generation are always deleted after export, even on failure.
