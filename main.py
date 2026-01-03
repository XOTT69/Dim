import os
import time
import socket
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from telegram import Bot

# ===== НАЛАШТУВАННЯ =====
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])

HOST = "grigorivkasvitbo97.tplinkdns.com"
CHECK_INTERVAL = 30      # перевірка кожні 30 сек
STABLE_SECONDS = 60      # антифлап 1 хв

bot = Bot(BOT_TOKEN)

last_state = None
last_change = None
power_off_time = None


def router_alive(host: str) -> bool:
    """
    True  -> роутер реально онлайн
    False -> роутер вимкнений / світла нема
    """
    try:
        ip = socket.gethostbyname(host)
        s = socket.create_connection((ip, 80), timeout=3)
        s.close()
        return True
    except:
        return False


def now_kyiv():
    return datetime.now(ZoneInfo("Europe/Kyiv"))


def fmt_time(dt):
    return dt.strftime("%d.%m %H:%M")


def fmt_duration(seconds):
    td = timedelta(seconds=seconds)
    h, r = divmod(td.seconds, 3600)
    m, _ = divmod(r, 60)
    if h:
        return f"{h} год {m} хв"
    return f"{m} хв"


async def send(text: str):
    await bot.send_message(chat_id=CHAT_ID, text=text)


async def main():
    global last_state, last_change, power_off_time

    await send("🤖 Світлобот запущено")

    while True:
        state = router_alive(HOST)
        now_ts = time.time()

        if last_state is None:
            last_state = state
            last_change = now_ts

        elif state != last_state:
            if last_change is None:
                last_change = now_ts

            elif now_ts - last_change >= STABLE_SECONDS:
                # 🔴 світло зникло
                if last_state and not state:
                    power_off_time = now_kyiv()
                    await send(f"🔴 Світло зникло ({fmt_time(power_off_time)})")

                # 🟢 світло зʼявилось
                elif not last_state and state and power_off_time:
                    duration = int((now_kyiv() - power_off_time).total_seconds())
                    await send(
                        f"🟢 Світло зʼявилось ({fmt_time(now_kyiv())})\n"
                        f"⏱ Не було: {fmt_duration(duration)}"
                    )
                    power_off_time = None

                last_state = state
                last_change = None
        else:
            last_change = None

        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
