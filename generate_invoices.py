"""
generate_invoices.py — runs at 23:59 every day via cron
Collects all new registrations from today, generates invoices, saves to pending.json
"""
import os
import json
import random
import string
from datetime import datetime, timedelta
import sheets
from invoice import generate_invoice_pdf
import config



def get_full_name(row):
    first = row.get("First name (include middle name, if applicable)\n名（漢字）", "").strip()
    last = row.get("Last name\n姓（漢字）", "").strip()
    return f"{first} {last}".strip()

def get_full_name_japanese(row):
    first = row.get("First name (include middle name, if applicable)\n名（漢字）", "").strip()
    last = row.get("Last name\n姓（漢字）", "").strip()
    return f"{last}{first}".strip()

def get_email(row):
    return (
        row.get("Email address・メールアドレス", "")
        or row.get("Email Address", "")
    ).strip()


def get_google_email(row):
    return row.get("Email Address", "").strip()


def get_committee(row):
    return row.get(
        "Which committee are you applying for? Please select your first choice.\nどの委員会に応募されますか？第一希望を選択してください。",
        "Unknown Committee"
    ).strip()


def run():
    print(f"[{datetime.now()}] Night job starting...")

    applications = sheets.get_new_applications()
    if not applications:
        print("No new applications today.")
        return

    print(f"Found {len(applications)} new application(s).")

    send_date = datetime.now()
    date_str = send_date.strftime("%Y-%m-%d")
    deadline_str = (send_date + timedelta(days=7)).strftime("%Y-%m-%d")

    os.makedirs(config.PDF_OUTPUT_DIR, exist_ok=True)

    # Always start fresh each night
    pending = []

    for row in applications:
        full_name = get_full_name(row)
        full_name_ja = get_full_name_japanese(row)
        email = get_email(row)
        google_email = get_google_email(row)
        committee = get_committee(row)
        row_index = row["_row_index"]

        random_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        pdf_path = os.path.join(
            config.PDF_OUTPUT_DIR,
            f"NUMUN2026_Invoice_{random_id}.pdf"
        )

        print(f"Generating invoice for {full_name}...")
        generate_invoice_pdf(
            full_name=full_name,
            full_name_ja=full_name_ja,
            date_str=date_str,
            deadline_str=deadline_str,
            output_path=pdf_path
        )

        sheets.mark_as_processed(row_index, status="PENDING_APPROVAL")

        pending.append({
            "full_name": full_name,
            "full_name_ja": full_name_ja,
            "email": email,
            "google_email": google_email,
            "committee": committee,
            "deadline": deadline_str,
            "pdf_path": pdf_path,
            "row_index": row_index,
            "approved": False,
            "emailed": False,
            "discord_message_id": None
        })
        print(f"Invoice ready for {full_name}")

    with open(config.PENDING_FILE, "w") as f:
        json.dump(pending, f, indent=2, ensure_ascii=False)

    print(f"[{datetime.now()}] Night job done. {len(applications)} invoice(s) queued.")


if __name__ == "__main__":
    run()
