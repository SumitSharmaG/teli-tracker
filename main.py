import os
import asyncio
from datetime import datetime
from threading import Thread
import pytz
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.tl.functions.users import GetUsersRequest
from telethon.tl.types import UserStatusOnline, UserStatusRecently, UserStatusOffline, UserStatusLastWeek

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
TARGET_USER = os.environ.get("TARGET_USER")
ALERT_RECEIVER = os.environ.get("ALERT_RECEIVER")

IST = pytz.timezone('Asia/Kolkata')

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

def get_ist_now():
    return datetime.now(IST)

async def send_alert(message):
    try:
        await client.send_message(alert_dest_id, message, parse_mode='html')
    except Exception as e:
        print(f"Alert error: {e}")

async def live_tracker_loop():
    global is_currently_online, session_start_time
    target_input = await client.get_input_entity(TARGET_USER)

    while True:
        try:
            # 1. Host ko server par continuously active socket me rakhna
            await client(UpdateStatusRequest(offline=False))

            # 2. Raw level par target ki state fetch karna
            users = await client(GetUsersRequest(id=[target_input]))
            if users:
                user = users[0]
                status = user.status
                now = get_ist_now()

                # User Online State Detect Hui
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

                # User Offline / Recently Switch Hua
                elif isinstance(status, (UserStatusRecently, UserStatusOffline, UserStatusLastWeek)):
                    if is_currently_online:
                        is_currently_online = False
                        start_time = session_start_time or now
                        session_start_time = None

                        duration = int((now - start_time).total_seconds())
                        minutes, seconds = divmod(duration, 60)
                        offline_time_str = now.strftime('%I:%M:%S %p')

                        msg = (
                            f"🔴 <b>@{TARGET_USER} Offline Ho Gaya!</b>\n"
                            f"⏰ Left at: <code>{offline_time_str}</code>\n"
                            f"⏱ Active Duration: <code>{minutes}m {seconds}s</code>"
                        )
                        await send_alert(msg)

        except Exception as e:
            print(f"Tracking error: {e}")

        # Fast polling interval (4 seconds)
        await asyncio.sleep(4)

async def start_tracker():
    global alert_dest_id
    await client.start()

    receiver_entity = await client.get_entity(ALERT_RECEIVER)
    alert_dest_id = receiver_entity.id

    startup_msg = (
        f"🚀 <b>Live Tracker Started!</b>\n"
        f"🎯 Target: @{TARGET_USER}\n"
        f"⚡ Fast Poller & Live Socket: Active\n"
        f"🇮🇳 Clock: IST (Asia/Kolkata)"
    )
    await send_alert(startup_msg)
    await live_tracker_loop()

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
