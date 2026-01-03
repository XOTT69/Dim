import os
import time
import socket
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from telegram import Bot

# ===== НАЛАШТУВАННЯ =====
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])

HOST = "grigorivkasvitbo97.tplinkdns.com"
CHECK_INTERVAL = 30      # секунд
STABLE_SECONDS = 60      # антифлап (1 хв)

bot = Bot(BOT_TOKEN)

last_state = None
last_change = None
power_off_time = None

def dns_alive(host):
    try:
        socket.gethostbyname(host)
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

bot.send_message(CHAT_ID, "🤖 Світлобот запущено")

while True:
    state = dns_alive(HOST)
    now = time.time()

    if last_state is None:
        last_state = state
        last_change = now

    elif state != last_state:
        # фіксуємо зміну, але чекаємо стабільність
        if last_change is None:
            last_change = now

        elif now - last_change >= STABLE_SECONDS:
            # 🔴 світло зникло
            if last_state and not state:
                power_off_time = now_kyiv()
                bot.send_message(
                    CHAT_ID,
                    f"🔴 Світло зникло ({fmt_time(power_off_time)})"
                )

            # 🟢 світло зʼявилось
            elif not last_state and state and power_off_time:
                duration = int((now_kyiv() - power_off_time).total_seconds())
                bot.send_message(
                    CHAT_ID,
                    f"🟢 Світло зʼявилось ({fmt_time(now_kyiv())})\n"
                    f"⏱ Не було: {fmt_duration(duration)}"
                )
                power_off_time = None

            last_state = state
            last_change = None
    else:
        last_change = None

    time.sleep(CHECK_INTERVAL)
