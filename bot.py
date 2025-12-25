import time
import socket
import requests
import subprocess
import platform
from datetime import datetime
from zoneinfo import ZoneInfo
import threading
import os

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = "-1003534080985"              # твій канал/чат

DDNS_HOST = "home-ax53u.asuscomm.com"   # Asus DDNS
DEVICE_IP = "192.168.50.254"            # Espressif без ДБЖ

CHECK_INTERVAL = 60                     # сек, пауза між перевірками
TIMEOUT = 4
FAIL_CONFIRM = 3                        # скільки разів підряд має впасти перевірка
# ==================================================

last_state = None                       # "ON", "OFF", "NET_DOWN"
power_off_at = None
fail_count_power = 0
fail_count_net = 0


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


def kyiv_time():
    return datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%H:%M")


def format_duration(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    return f"{h} год {m} хв" if h else f"{m} хв"


# ========== НИЗЬКОРІВНЕВІ ЧЕКИ =====================

def tcp_check(host, port):
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT):
            return True
    except OSError:
        return False


def internet_alive():
    # Google DNS як простий індикатор інтернету.[web:45]
    return tcp_check("8.8.8.8", 53)


def ddns_alive():
    try:
        ip = socket.gethostbyname(DDNS_HOST)
    except OSError as e:
        print("DDNS resolve error:", repr(e))
        return False
    ok = tcp_check(ip, 443)
    if not ok:
        print("DDNS TCP error to", ip)
    return ok


def device_alive():
    # Пінг Espressif по локальному IP; якщо нема відповіді — девайс вимкнувся з 220В.
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        result = subprocess.run(
            ["ping", param, "1", DEVICE_IP],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT
        )
        return result.returncode == 0
    except Exception as e:
        print("Ping error:", repr(e))
        return False
# =====================================================


def get_status_text():
    net_ok = internet_alive() and ddns_alive()
    dev_ok = device_alive()

    if not net_ok:
        return "🌐 Інтернет/роутер недоступні (можливо, сів ДБЖ)"
    if dev_ok:
        return "🔌 Світло Є"
    else:
        return "⚡ Світла НЕМА (Espressif офлайн)"


def handle_updates():
    offset = None
    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35
            ).json()
        except Exception as e:
            print("getUpdates error:", repr(e))
            time.sleep(5)
            continue

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
    global last_state, power_off_at, fail_count_power, fail_count_net

    while True:
        net_ok = internet_alive() and ddns_alive()
        dev_ok = device_alive()

        state = last_state

        # Лічильник падінь інтернету/роутера
        if not net_ok:
            fail_count_net += 1
        else:
            fail_count_net = 0

        if net_ok:
            # Інтернет є → дивимось на Espressif
            if dev_ok:
                fail_count_power = 0
                state = "ON"
            else:
                fail_count_power += 1
                if fail_count_power >= FAIL_CONFIRM:
                    state = "OFF"
        else:
            # Інтернет/роутер лежать
            if fail_count_net >= FAIL_CONFIRM:
                state = "NET_DOWN"

        if state != last_state:
            now = kyiv_time()

            if state == "OFF":
                power_off_at = time.time()
                send_message(f"⚡ Світло зникло — {now}", True)

            elif state == "ON" and last_state == "OFF":
                duration = int(time.time() - power_off_at) if power_off_at else 0
                send_message(
                    f"🔌 Світло зʼявилось — {now}\n"
                    f"⏱️ Не було світла: {format_duration(duration)}",
                    True
                )

            elif state == "NET_DOWN":
                send_message(f"🌐 Пропав інтернет/роутер — {now}", True)

            elif state == "ON" and last_state == "NET_DOWN":
                send_message(f"🌐 Інтернет/роутер відновились — {now}", True)

            last_state = state

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    print("🚀 СвітлоБот (DDNS + Espressif 192.168.50.254) запущено")
    threading.Thread(target=handle_updates, daemon=True).start()
    monitor_power()
