import os
import time
import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

CMC_API_KEY = os.getenv("COINMARKETCAP_API_KEY")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELE_TOKEN)
BASE_URL = "https://pro-api.coinmarketcap.com/v1"

def fetch_top_coins(limit=500, start=1):
    url = f"{BASE_URL}/cryptocurrency/listings/latest"
    params = {
        "start": start,
        "limit": limit,
        "convert": "USD"
    }
    headers = {
        "X-CMC_PRO_API_KEY": CMC_API_KEY
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()["data"]

def fetch_and_send_top_flow():
    all_coins = []
    # CoinMarketCap 每次最多返回 500 条，前1000条需要两次请求
    all_coins += fetch_top_coins(limit=500, start=1)
    all_coins += fetch_top_coins(limit=500, start=501)

    results = []
    for coin in all_coins:
        # 使用 24h 交易量变化作为资金流入/流出指标
        volume_change = coin.get("quote", {}).get("USD", {}).get("volume_change_24h", 0)
        results.append((coin["name"], volume_change))

    # TOP20 净流入
    inflow = sorted([c for c in results if c[1] > 0], key=lambda x: x[1], reverse=True)[:20]
    # TOP20 净流出
    outflow = sorted([c for c in results if c[1] < 0], key=lambda x: x[1])[:20]

    msg = "⏰ 资金净流入 TOP20\n"
    for i, (name, val) in enumerate(inflow, 1):
        msg += f"{i}. {name} +{val:,.2f}\n"

    msg += "\n⏰ 资金净流出 TOP20\n"
    for i, (name, val) in enumerate(outflow, 1):
        msg += f"{i}. {name} {val:,.2f}\n"

    bot.send_message(chat_id=CHAT_ID, text=msg)

if __name__ == "__main__":
    while True:
        try:
            fetch_and_send_top_flow()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(3600)  # 每1小时执行一次
