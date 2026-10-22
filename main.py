import os
import asyncio
import datetime
from threading import Thread
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import (
    UserStatusOnline,
    UserStatusOffline,
    UserStatusRecently,
    UserStatusLastWeek
)

# Render Environment Variables se fetch karna (Zero hardcoded secrets)
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
TARGET_USER = os.environ.get("TARGET_USER")
ALERT_RECEIVER = os.environ.get("ALERT_RECEIVER")

# Dummy Flask Web Server (Render port binding ke liye zaroori)
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Tracker is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Telethon client initialized via StringSession
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

online_sessions = {}
target_id = None
alert_dest_id = None

@client.on(events.UserUpdate)
async def handler(event):
    if event.user_id != target_id:
        return

    now = datetime.datetime.now()
    status = event.status

    # Case 1: User Online Aaya
    if event.online or isinstance(status, UserStatusOnline):
        if event.user_id not in online_sessions:
            online_sessions[event.user_id] = now
            time_str = now.strftime('%I:%M:%S %p')
            msg = (
                f"🟢 <b>@{TARGET_USER} Active Aaya!</b>\n"
                f"⏰ Start Time: <code>{time_str}</code>"
            )
            await client.send_message(alert_dest_id, msg, parse_mode='html')

    # Case 2: User Offline Gaya (Dono privacy types: Exact ya Hidden 'Recently')
    elif (
        event.offline 
        or isinstance(status, (UserStatusOffline, UserStatusRecently, UserStatusLastWeek))
    ):
        if event.user_id in online_sessions:
            start_time = online_sessions.pop(event.user_id)
            offline_time = now

            duration = offline_time - start_time
            minutes, seconds = divmod(duration.total_seconds(), 60)
            duration_str = f"{int(minutes)}m {int(seconds)}s"
            offline_time_str = offline_time.strftime('%I:%M:%S %p')

            privacy_info = "Last Seen Recently" if isinstance(status, UserStatusRecently) else "Standard"

            msg = (
                f"🔴 <b>@{TARGET_USER} Offline Ho Gaya!</b>\n"
                f"⏰ Left at: <code>{offline_time_str}</code>\n"
                f"⏱ Total Active: <code>{duration_str}</code>\n"
                f"🔒 Privacy Mode: <i>{privacy_info}</i>"
            )
            await client.send_message(alert_dest_id, msg, parse_mode='html')

async def start_tracker():
    global target_id, alert_dest_id
    await client.start()

    target_entity = await client.get_entity(TARGET_USER)
    target_id = target_entity.id

    receiver_entity = await client.get_entity(ALERT_RECEIVER)
    alert_dest_id = receiver_entity.id

    startup_msg = (
        f"🚀 <b>Tracker Service Started!</b>\n"
        f"🎯 Target: @{TARGET_USER}\n"
        f"✅ Render Host Active."
    )
    await client.send_message(alert_dest_id, startup_msg, parse_mode='html')
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Flask thread start karna
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Telethon loop run karna
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_tracker())
