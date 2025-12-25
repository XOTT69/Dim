import time
import socket
import requests
from datetime import datetime
import threading
import os

# ====== НАЛАШТУВАННЯ ======
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = "-1003534080985"

DDNS_HOST = "home-ax53u.asuscomm.com"

CHECK_INTERVAL = 60
TIMEOUT = 4
# =========================

last_state = None
power_off_at = None


def tg(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    return requests.post(url, json=payload, timeout=10)


def send_message(text, with_button=False):
    payload = {"chat_id": CHAT_ID, "text": text}

    if with_button:
        payload["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "📊 Статус", "callback_data": "status"}
            ]]
        }

    tg("sendMessage", payload)


# ====== DDNS CHECK (СТАБІЛЬНИЙ) ======
def ddns_alive():
    try:
        ip = socket.gethostbyname(DDNS_HOST)
        socket.create_connection((ip, 443), timeout=TIMEOUT)
        return True
    except:
        return False
# ====================================


def get_status_text():
    return "🔌 Світло Є" if ddns_alive() else "⚡ Світла НЕМА"


def format_duration(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    return f"{h} год {m} хв" if h else f"{m} хв"


def handle_updates():
    offset = None

    while True:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 30},
            timeout=35
        ).json()

        for u in r.get("result", []):
            offset = u["update_id"] + 1

            if "message" in u and u["message"].get("text") == "/status":
                send_message(get_status_text(), with_button=True)

            if "callback_query" in u:
                if u["callback_query"]["data"] == "status":
                    tg("answerCallbackQuery", {
                        "callback_query_id": u["callback_query"]["id"]
                    })
                    send_message(get_status_text(), with_button=True)

        time.sleep(1)


def monitor_power():
    global last_state, power_off_at

    while True:
        state = "ON" if ddns_alive() else "OFF"

        if state != last_state:
            now = datetime.now().strftime("%H:%M")

            if state == "OFF":
                power_off_at = time.time()
                send_message(f"⚡ Світло зникло — {now}", True)

            elif state == "ON" and last_state == "OFF":
                duration = int(time.time() - power_off_at)
                send_message(
                    f"🔌 Світло зʼявилось — {now}\n"
                    f"⏱️ Не було світла: {format_duration(duration)}",
                    True
                )

            last_state = state

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    print("🚀 СвітлоБот (DDNS-only) запущено")
    threading.Thread(target=handle_updates, daemon=True).start()
    monitor_power()
