import os
import time
import asyncio
import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

CMC_API_KEY = os.getenv("COINMARKETCAP_API_KEY")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = "https://pro-api.coinmarketcap.com/v1"

bot = Bot(token=TELE_TOKEN)

HEADERS = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": CMC_API_KEY,
}

def get_top_coins(limit=1000):
    url = f"{BASE_URL}/cryptocurrency/listings/latest"
    params = {
        "start": 1,
        "limit": limit,
        "convert": "USD",
    }
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()["data"]

def compute_fundflow(coins):
    """
    使用24h的volume_change_pct作为近似资金流向
    """
    results = []
    for coin in coins:
        change_pct = coin.get("quote", {}).get("USD", {}).get("volume_change_24h", 0)
        results.append((coin["name"], change_pct))
    return results

async def send_telegram(msg):
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def fetch_and_send():
    coins = get_top_coins(limit=1000)
    results = compute_fundflow(coins)

    inflow = sorted([c for c in results if c[1] > 0], key=lambda x: x[1], reverse=True)[:20]
    outflow = sorted([c for c in results if c[1] < 0], key=lambda x: x[1])[:20]

    msg = "⏰ 资金净流入 TOP20\n"
    for i, (name, val) in enumerate(inflow, 1):
        msg += f"{i}. {name} +{val:,.2f}%\n"

    msg += "\n⏰ 资金净流出 TOP20\n"
    for i, (name, val) in enumerate(outflow, 1):
        msg += f"{i}. {name} {val:,.2f}%\n"

    await send_telegram(msg)
    print("已发送 Telegram 消息")

async def main_loop():
    while True:
        try:
            await fetch_and_send()
        except Exception as e:
            print(f"出错: {e}")
        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
