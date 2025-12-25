import time
import socket
import requests
from datetime import datetime

# ====== НАЛАШТУВАННЯ ======
BOT_TOKEN = "8413003519:AAHLrlYJZPRFeSyslhQalYNS5Uz5qh8jZn8"  # ✅ Твій токен
CHAT_ID = "-1003534080985"   # канал
DDNS_HOST = "yourname.asuscomm.com"

DEVICES = [
    "192.168.50.2",      # Tuya (P100)
    "192.168.50.254"     # Espressif
]

CHECK_INTERVAL = 60
TIMEOUT = 3
# =========================

last_state = None
power_off_at = None


def tg(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    return requests.post(url, json=payload, timeout=10)


def send_message(text, with_button=False):
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    if with_button:
        payload["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "📊 Статус", "callback_data": "status"}
            ]]
        }

    tg("sendMessage", payload)


def host_alive(host):
    try:
        socket.create_connection((host, 80), timeout=TIMEOUT)
        return True
    except:
        return False


def any_device_alive():
    for ip in DEVICES:
        try:
            socket.create_connection((ip, 80), timeout=TIMEOUT)
            return True
        except:
            pass
    return False


def get_status_text():
    router = host_alive(DDNS_HOST)

    if not router:
        return "❓ Статус невідомий\n(роутер недоступний)"

    devices = any_device_alive()

    if devices:
        return "🔌 Світло Є"
    else:
        return "⚡ Світла НЕМА"


def format_duration(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    return f"{h} год {m} хв" if h else f"{m} хв"


def handle_updates():
    global last_state, power_off_at

    offset = None

    while True:
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset

        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params=params,
            timeout=35
        ).json()

        for update in r.get("result", []):
            offset = update["update_id"] + 1

            # /status
            if "message" in update:
                text = update["message"].get("text", "")
                if text == "/status":
                    send_message(get_status_text(), with_button=True)

            # кнопка
            if "callback_query" in update:
                if update["callback_query"]["data"] == "status":
                    tg("answerCallbackQuery", {
                        "callback_query_id": update["callback_query"]["id"]
                    })
                    send_message(get_status_text(), with_button=True)

        time.sleep(1)


def monitor_power():
    global last_state, power_off_at

    while True:
        router = host_alive(DDNS_HOST)

        if router:
            devices = any_device_alive()
            state = "ON" if devices else "OFF"
        else:
            state = "UNKNOWN"

        if state != last_state:
            now = datetime.now().strftime("%H:%M")

            if state == "OFF":
                power_off_at = time.time()
                send_message(f"⚡ Світло зникло — {now}", with_button=True)

            elif state == "ON" and last_state == "OFF":
                duration = int(time.time() - power_off_at)
                send_message(
                    f"🔌 Світло зʼявилось — {now}\n"
                    f"⏱️ Не було світла: {format_duration(duration)}",
                    with_button=True
                )

            last_state = state

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    import threading

    print("🚀 СвітлоБот запущено!")
    threading.Thread(target=handle_updates, daemon=True).start()
    monitor_power()
