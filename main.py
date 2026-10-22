import os
import asyncio
import datetime
from threading import Thread
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.users import GetFullUserRequest
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

app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Ghost Tracker is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

is_currently_online = False
session_start_time = None
alert_dest_id = None

async def send_alert(message):
    try:
        await client.send_message(alert_dest_id, message, parse_mode='html')
    except Exception as e:
        print(f"Alert error: {e}")

async def monitor_target():
    global is_currently_online, session_start_time
    
    # Bina number save kiye seedha username resolve karna
    target_input = await client.get_input_entity(TARGET_USER)
    
    while True:
        try:
            # Yeh wahi command hai jo chat open karne par Telegram chalata hai
            full_user = await client(GetFullUserRequest(target_input))
            user = full_user.users[0]
            status = user.status
            now = datetime.datetime.now()

            # 1. User Online Aaya
            if isinstance(status, UserStatusOnline):
                if not is_currently_online:
                    is_currently_online = True
                    session_start_time = now
                    time_str = now.strftime('%I:%M:%S %p')
                    msg = (
                        f"🟢 <b>@{TARGET_USER} Online Aaya!</b>\n"
                        f"⏰ Time: <code>{time_str}</code>"
                    )
                    await send_alert(msg)

            # 2. User Offline Gaya (Recently ya Exact last seen)
            elif isinstance(status, (UserStatusOffline, UserStatusRecently, UserStatusLastWeek)):
                if is_currently_online:
                    is_currently_online = False
                    start_time = session_start_time or now
                    session_start_time = None

                    duration = now - start_time
                    minutes, seconds = divmod(duration.total_seconds(), 60)
                    duration_str = f"{int(minutes)}m {int(seconds)}s"
                    offline_time_str = now.strftime('%I:%M:%S %p')

                    privacy_type = "Last seen recently" if isinstance(status, UserStatusRecently) else "Standard"

                    msg = (
                        f"🔴 <b>@{TARGET_USER} Offline Ho Gaya!</b>\n"
                        f"⏰ Left at: <code>{offline_time_str}</code>\n"
                        f"⏱ Active Duration: <code>{duration_str}</code>\n"
                        f"🔒 Mode: <i>{privacy_type}</i>"
                    )
                    await send_alert(msg)

        except Exception as e:
            print(f"Tracking error: {e}")

        # Telegram rate-limit se bachne ke liye 10-12 second ka gap ideal hai
        await asyncio.sleep(12)

async def start_tracker():
    global alert_dest_id
    await client.start()

    receiver_entity = await client.get_entity(ALERT_RECEIVER)
    alert_dest_id = receiver_entity.id

    startup_msg = (
        f"🚀 <b>Ghost Tracker Started!</b>\n"
        f"🎯 Target: @{TARGET_USER}\n"
        f"👻 Mode: Zero Message / No Contact Saved"
    )
    await send_alert(startup_msg)
    await monitor_target()

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
