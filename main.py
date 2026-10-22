import os
import asyncio
from datetime import datetime
from threading import Thread
import pytz
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.tl.functions.users import GetUsersRequest
from telethon.tl.types import (
    UserStatusOnline,
    UserStatusOffline,
    UserStatusRecently,
    UserStatusLastWeek
)

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
TARGET_USER = os.environ.get("TARGET_USER")
ALERT_RECEIVER = os.environ.get("ALERT_RECEIVER")

IST = pytz.timezone('Asia/Kolkata')

app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Deep Tracker is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

is_currently_online = False
session_start_time = None
target_id = None
alert_dest_id = None

def get_ist_now():
    return datetime.now(IST)

async def send_alert(message):
    try:
        await client.send_message(alert_dest_id, message, parse_mode='html')
    except Exception as e:
        print(f"Alert error: {e}")

async def handle_status_change(status):
    global is_currently_online, session_start_time
    now = get_ist_now()

    # User Online Detect Hua
    if isinstance(status, UserStatusOnline):
        if not is_currently_online:
            is_currently_online = True
            session_start_time = now
            time_str = now.strftime('%I:%M:%S %p')
            msg = (
                f"🟢 <b>@{TARGET_USER} Active Aaya!</b>\n"
                f"⏰ Start Time: <code>{time_str}</code>"
            )
            await send_alert(msg)

    # User Offline / Recently Detect Hua
    elif isinstance(status, (UserStatusOffline, UserStatusRecently, UserStatusLastWeek)):
        if is_currently_online:
            is_currently_online = False
            start_time = session_start_time or now
            session_start_time = None

            duration = now - start_time
            total_seconds = int(duration.total_seconds())
            minutes, seconds = divmod(total_seconds, 60)
            duration_str = f"{minutes}m {seconds}s"
            offline_time_str = now.strftime('%I:%M:%S %p')

            mode = "Nobody (Recently)" if isinstance(status, UserStatusRecently) else "Standard"

            msg = (
                f"🔴 <b>@{TARGET_USER} Offline Ho Gaya!</b>\n"
                f"⏰ Left at: <code>{offline_time_str}</code>\n"
                f"⏱ Active Duration: <code>{duration_str}</code>\n"
                f"🔒 Mode: <i>{mode}</i>"
            )
            await send_alert(msg)

# Loop 1: Host Presence Heartbeat (Host ko online dikhana taaki reciprocal packets unlock hon)
async def keep_host_online_loop():
    while True:
        try:
            # Server ko batana ki Host live active hai
            await client(UpdateStatusRequest(offline=False))
        except Exception as e:
            print(f"Heartbeat warning: {e}")
        await asyncio.sleep(45)

# Loop 2: Raw User Presence Check
async def deep_status_poller():
    target_input = await client.get_input_entity(TARGET_USER)
    while True:
        try:
            # Direct raw user entity status query
            result = await client(GetUsersRequest(id=[target_input]))
            if result:
                user = result[0]
                if user.status:
                    await handle_status_change(user.status)
        except Exception as e:
            print(f"Poller warning: {e}")

        # 6 se 7 second ka fast interval taaki brief online sessions miss na hon
        await asyncio.sleep(6)

# Real-time event fallback
@client.on(events.UserUpdate)
async def user_event_handler(event):
    if event.user_id == target_id and event.status:
        await handle_status_change(event.status)

async def start_tracker():
    global target_id, alert_dest_id
    await client.start()

    target_entity = await client.get_entity(TARGET_USER)
    target_id = target_entity.id

    receiver_entity = await client.get_entity(ALERT_RECEIVER)
    alert_dest_id = receiver_entity.id

    startup_msg = (
        f"🚀 <b>Deep Presence Tracker Live!</b>\n"
        f"🎯 Target: @{TARGET_USER}\n"
        f"⚡ Active Host Heartbeat: Enabled\n"
        f"🇮🇳 Timezone: IST"
    )
    await send_alert(startup_msg)

    # Dono background loops execute karna
    asyncio.create_task(keep_host_online_loop())
    asyncio.create_task(deep_status_poller())

    await client.run_until_disconnected()

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(start_tracker())
