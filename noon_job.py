"""
noon_job.py — runs at 12:00 every day via cron
Posts all pending invoices to Discord for EA approval
"""
import os
import json
import asyncio
import discord
import config
from datetime import datetime

PENDING_FILE = "pending.json"

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"[{datetime.now()}] Noon job: Discord connected as {client.user}")
    await post_pending_invoices()


async def post_pending_invoices():
    if not os.path.exists(PENDING_FILE):
        print("No pending file found.")
        await client.close()
        return

    with open(PENDING_FILE, "r") as f:
        pending = json.load(f)

    unposted = [p for p in pending if not p["approved"] and not p["emailed"] and p["discord_message_id"] is None]

    if not unposted:
        print("No new invoices to post.")
        await client.close()
        return

    channel = client.get_channel(config.DISCORD_CHANNEL_ID)
    if channel is None:
        print(f"ERROR: Channel {config.DISCORD_CHANNEL_ID} not found.")
        await client.close()
        return

    for entry in unposted:
        content = (
            f"📋 **New NUMUN 2026 Application**\n"
            f"**Name:** {entry['full_name']}\n"
            f"**Email:** {entry['email']}\n"
            f"**Committee:** {entry['committee']}\n"
            f"**Payment Deadline:** {entry['deadline']}\n\n"
            f"React with ✅ to approve sending the invoice email."
        )
        file = discord.File(entry["pdf_path"], filename=os.path.basename(entry["pdf_path"]))
        message = await channel.send(content=content, file=file)

        # Save message ID so afternoon job knows which ones were approved
        entry["discord_message_id"] = str(message.id)
        print(f"Posted invoice for {entry['full_name']} (message ID: {message.id})")

    with open(PENDING_FILE, "w") as f:
        json.dump(pending, f, indent=2)

    print(f"[{datetime.now()}] Noon job done. {len(unposted)} invoice(s) posted to Discord.")
    await client.close()


if __name__ == "__main__":
    client.run(config.DISCORD_BOT_TOKEN)
