import asyncio
import random
import requests
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
TELEGRAM_TOKEN  = "PUT_YOUR_NEW_TOKEN_HERE"   # ⚠️ regenerate the old one!
CHAT_ID         = -1003253943368
SIGNAL_INTERVAL = 5 * 60   # 5 minutes

UTC_OFFSET = 3   # UTC+3

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD"]

PAIR_MAP = {
    "EUR/USD": ("EUR", "USD"),
    "GBP/USD": ("GBP", "USD"),
    "USD/JPY": ("USD", "JPY"),
    "USD/CHF": ("USD", "CHF"),
    "AUD/USD": ("AUD", "USD"),
    "USD/CAD": ("USD", "CAD"),
}

price_history: dict[str, list[float]] = {pair: [] for pair in PAIRS}
MAX_HISTORY = 20


# ─────────────────────────────────────────────
# FETCH PRICES
# ─────────────────────────────────────────────
def fetch_prices() -> dict:
    prices = {}
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        r.raise_for_status()
        rates = r.json().get("rates", {})
        for pair, (base, quote) in PAIR_MAP.items():
            if base == "USD":
                rate = rates.get(quote)
                if rate:
                    prices[pair] = round(rate, 5)
            else:
                rate = rates.get(base)
                if rate:
                    prices[pair] = round(1 / rate, 5)
    except Exception as e:
        print(f"[Price fetch error] {e}")
    return prices


# ─────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────
def compute_rsi(prices: list[float], period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = prices[-i] - prices[-i - 1]
        (gains if diff > 0 else losses).append(abs(diff))
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def compute_ma(prices: list[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 5)


# ─────────────────────────────────────────────
# SIGNAL LOGIC  → returns direction + strength
# ─────────────────────────────────────────────
def generate_signal(pair: str, current_price: float) -> dict | None:
    history = price_history[pair]
    history.append(current_price)
    if len(history) > MAX_HISTORY:
        history.pop(0)

    rsi  = compute_rsi(history)
    ma5  = compute_ma(history, 5)
    ma10 = compute_ma(history, 10)

    if rsi is None or ma5 is None or ma10 is None:
        return None   # not enough data → no signal

    direction = None
    strength  = 50

    if rsi < 35 and ma5 > ma10:
        direction, strength = "CALL", 88
    elif rsi > 65 and ma5 < ma10:
        direction, strength = "PUT", 88
    elif ma5 > ma10:
        direction, strength = "CALL", 72
    elif ma5 < ma10:
        direction, strength = "PUT", 72
    else:
        return None

    return {"direction": direction, "strength": strength}


# ─────────────────────────────────────────────
# BUILD VIP MESSAGE (Arabic)
# ─────────────────────────────────────────────
def strength_bar(percent: int) -> str:
    filled = round(percent / 10)
    return "█" * filled + "▒" * (10 - filled)


def build_vip_message(pair: str, info: dict) -> str:
    tz = timezone(timedelta(hours=UTC_OFFSET))
    now = datetime.now(tz)

    # entry time = a few minutes from now
    entry = now + timedelta(minutes=4)
    entry_str = entry.strftime("%H:%M")

    # countdown text
    countdown = "03:59 دقيقة"

    if info["direction"] == "PUT":
        dir_text = "🔴 هبوط (PUT)"
    else:
        dir_text = "🟢 صعود (CALL)"

    bar = strength_bar(info["strength"])

    msg = (
        f"🔥 تنبيه إشارة قادمة (VIP)\n\n"
        f"📊 الزوج: {pair}-OTC\n"
        f"🕐 وقت الدخول: {entry_str} (UTC+{UTC_OFFSET})\n"
        f"⏳ الفريم: M1\n"
        f"🧭 الاتجاه: {dir_text}\n\n"
        f"💪 قوة الإشارة: {bar} {info['strength']}%\n\n"
        f"✋ استعد للدخول بعد: {countdown}\n\n"
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
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    if not r.ok:
        print(f"[Telegram error] {r.status_code}: {r.text}")
    else:
        print("  ✅ Signal sent")


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
async def main():
    print("🤖 VIP Signal Bot started")
    while True:
        try:
            prices = fetch_prices()
            if prices:
                # pick one pair that has a valid signal
                signals = []
                for pair, price in prices.items():
                    info = generate_signal(pair, price)
                    if info:
                        signals.append((pair, info))

                if signals:
                    pair, info = random.choice(signals)
                    send_telegram(build_vip_message(pair, info))
                else:
                    print("  No clear signal this round.")
            else:
                print("  No prices fetched.")
        except Exception as e:
            print(f"[Error] {e}")

        await asyncio.sleep(SIGNAL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
