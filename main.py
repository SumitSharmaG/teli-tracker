import asyncio
from datetime import datetime
import pytz
from telethon import TelegramClient
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.tl.functions.users import GetUsersRequest
from telethon.tl.types import UserStatusOnline, UserStatusRecently

IST = pytz.timezone('Asia/Kolkata')

async def test_live_tracker(client, target_username):
    target = await client.get_input_entity(target_username)
    is_online = False
    start_time = None

    print(f"[*] Monitoring started for {target_username}...")

    while True:
        try:
            # 1. Host ko server par continuously live rakhna
            await client(UpdateStatusRequest(offline=False))

            # 2. Raw level par target ki current state fetch karna
            users = await client(GetUsersRequest(id=[target]))
            user = users[0]
            current_status = user.status

            now = datetime.now(IST)

            # Check: Kya user online state me hai?
            if isinstance(current_status, UserStatusOnline):
                if not is_online:
                    is_online = True
                    start_time = now
                    print(f"🟢 [ONLINE DETECTED] Time: {now.strftime('%I:%M:%S %p')}")

            # Check: Kya user wapas recently (offline) ho gaya?
            elif isinstance(current_status, UserStatusRecently):
                if is_online:
                    is_online = False
                    duration = int((now - start_time).total_seconds())
                    print(f"🔴 [OFFLINE DETECTED] Left at: {now.strftime('%I:%M:%S %p')} | Active: {duration}s")

        except Exception as e:
            print(f"Error: {e}")

        # Fast check taaki transition miss na ho
        await asyncio.sleep(4)
racker())
