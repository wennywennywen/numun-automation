"""
send_approved_emails.py — runs at 13:00 every day via cron
Checks Discord for ✅ reactions, sends emails for approved invoices
"""
import os
import json
import discord
import config
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.gmail_sender import send_invoice_email
from core import sheets

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"[{datetime.now()}] Afternoon job: Discord connected as {client.user}")
    await check_and_send()


async def check_and_send():
    if not os.path.exists(config.PENDING_FILE):
        print("No pending file found.")
        await client.close()
        return

    with open(config.PENDING_FILE, "r", encoding="utf-8") as f:
        pending = json.load(f)

    channel = client.get_channel(config.DISCORD_CHANNEL_ID)
    if channel is None:
        print(f"ERROR: Channel {config.DISCORD_CHANNEL_ID} not found.")
        await client.close()
        return

    sent_count = 0
    for entry in pending:
        if entry["emailed"]:
            continue
        if not entry["discord_message_id"]:
            continue

        try:
            message = await channel.fetch_message(int(entry["discord_message_id"]))
        except discord.NotFound:
            print(f"Message not found for {entry['full_name']}, skipping.")
            continue

        approved = any(
            str(r.emoji) == "✅" and r.count > 0
            for r in message.reactions
        )

        if approved:
            # Send to both emails, deduplicated
            emails_to_send = {entry["email"]}
            if entry.get("google_email"):
                emails_to_send.add(entry["google_email"])

            for email_addr in emails_to_send:
                print(f"Sending email to {email_addr}...")
                send_invoice_email(
                    to_email=email_addr,
                    full_name=entry["full_name"],
                    full_name_ja=entry.get("full_name_ja", entry["full_name"]),
                    deadline_str=entry["deadline"],
                    pdf_path=entry["pdf_path"]
                )

            sheets.mark_as_processed(entry["row_index"], status="INVOICE_SENT")
            entry["emailed"] = True
            entry["approved"] = True
            await channel.send(f"📧 Invoice email sent to {entry['full_name']} ({', '.join(emails_to_send)}).")
            sent_count += 1
            print(f"Done for {entry['full_name']}")
        else:
            print(f"No approval yet for {entry['full_name']}, skipping.")

    with open(config.PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(pending, f, indent=2, ensure_ascii=False)

    print(f"[{datetime.now()}] Afternoon job done. {sent_count} email(s) sent.")
    await client.close()


if __name__ == "__main__":
    client.run(config.DISCORD_BOT_TOKEN)
