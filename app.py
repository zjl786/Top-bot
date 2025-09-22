import os
import time
import requests
import asyncio
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CMC_API_KEY = os.getenv("COINMARKETCAP_API_KEY")

bot = Bot(token=TELE_TOKEN)
BASE_URL = "https://pro-api.coinmarketcap.com/v1"

HEADERS = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": CMC_API_KEY
}

def get_top_coins(limit=1000):
    url = f"{BASE_URL}/cryptocurrency/listings/latest"
    params = {
        "start": "1",
        "limit": limit,
        "convert": "USD"
    }
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    data = r.json()
    return data["data"]

def get_fundflow(coin_id):
    # CoinMarketCap 没有直接资金流入API，这里用 24h 交易量变化作为替代
    url = f"{BASE_URL}/cryptocurrency/quotes/latest"
    params = {"id": coin_id, "convert": "USD"}
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    data = r.json()
    quote = data["data"][str(coin_id)]["quote"]["USD"]
    # 使用 24h volume_change_pct 作为“资金流指标”近似
    value = quote.get("volume_change_24h", 0)
    return value

async def send_telegram(msg):
    await bot.send_message(chat_id=CHAT_ID, text=msg)

def fetch_and_send():
    coins = get_top_coins(limit=1000)
    results = []
    for coin in coins:
        try:
            value = get_fundflow(coin["id"])
            results.append((coin["name"], value))
        except Exception:
            continue

    inflow = sorted([c for c in results if c[1] > 0], key=lambda x: x[1], reverse=True)[:20]
    outflow = sorted([c for c in results if c[1] < 0], key=lambda x: x[1])[:20]

    msg = "⏰ 资金净流入 TOP20\n"
    for i, (name, val) in enumerate(inflow, 1):
        msg += f"{i}. {name} +{val:,.2f}\n"

    msg += "\n⏰ 资金净流出 TOP20\n"
    for i, (name, val) in enumerate(outflow, 1):
        msg += f"{i}. {name} {val:,.2f}\n"

    asyncio.run(send_telegram(msg))

if __name__ == "__main__":
    fetch_and_send()
