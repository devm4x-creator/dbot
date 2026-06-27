import asyncio
import random
import requests
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
TELEGRAM_TOKEN  = "8699565279:AAHOOGtJDZE4ug0AVxuSBUIwDR-x6Fiegqw"
CHAT_ID         = -1003253943368
SIGNAL_INTERVAL = 5 * 60   # 5 minutes

UTC_OFFSET = 3   # UTC+3
ENTRY_DELAY_MIN = 5   # الصفقة بعد 5 دقائق من الإرسال

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD"]


# ─────────────────────────────────────────────
# GENERATE SIGNAL  (random direction + strength)
# ─────────────────────────────────────────────
def generate_signal() -> dict:
    pair = random.choice(PAIRS)
    direction = random.choice(["CALL", "PUT"])
    strength = random.choice([70, 72, 75, 78, 80, 82, 85, 88, 90])
    return {"pair": pair, "direction": direction, "strength": strength}


# ─────────────────────────────────────────────
# BUILD VIP MESSAGE (Arabic)
# ─────────────────────────────────────────────
def strength_bar(percent: int) -> str:
    filled = round(percent / 10)
    return "█" * filled + "▒" * (10 - filled)


def build_vip_message(info: dict) -> str:
    tz = timezone(timedelta(hours=UTC_OFFSET))
    now = datetime.now(tz)

    # وقت الدخول = 5 دقائق من الآن (وقت حقيقي)
    entry = now + timedelta(minutes=ENTRY_DELAY_MIN)
    entry_str = entry.strftime("%H:%M")
    now_str = now.strftime("%H:%M")

    if info["direction"] == "PUT":
        dir_text = "🔴 بيع "
    else:
        dir_text = "🟢 شراء "

    bar = strength_bar(info["strength"])

    msg = (
        f"🔥 تنبيه إشارة قادمة (VIP)\n\n"
        f"📊 الزوج: {info['pair']}-OTC\n"
        f"🎯 وقت الدخول: {entry_str} (UTC+{UTC_OFFSET})\n"
        f"⏳ الفريم: M1\n"
        f"🧭 الاتجاه: {dir_text}\n\n"
        f"✋ استعد للدخول بعد: {ENTRY_DELAY_MIN}:00 دقائق\n\n"
        f"🏛️ المنصة: Quotex\n"
        f"🛡️ خطة: بدون مضاعفات\n\n"
        f"⚠️ إدارة المخاطر أولاً: أي إشارة لا تعني ربحاً مضموناً. "
        f"التزم بحجم صفقة مناسب ولا تخاطر بأكثر مما تستطيع خسارته."
    )
    return msg


# ─────────────────────────────────────────────
# SEND TO TELEGRAM
# ─────────────────────────────────────────────
def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
        if not r.ok:
            print(f"[Telegram error] {r.status_code}: {r.text}")
        else:
            print("  ✅ Signal sent")
    except Exception as e:
        print(f"[Send error] {e}")


# ─────────────────────────────────────────────
# MAIN LOOP  → every 5 minutes
# ─────────────────────────────────────────────
async def main():
    print("🤖 VIP Signal Bot started")
    while True:
        try:
            info = generate_signal()
            send_telegram(build_vip_message(info))
        except Exception as e:
            print(f"[Error] {e}")

        await asyncio.sleep(SIGNAL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
