import os
import requests
from telegram import Bot
from dotenv import load_dotenv
import time

load_dotenv()

API_KEY = os.getenv("AICOIN_API_KEY")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = "https://open.aicoin.com/api/v2"  # 替换成实际接口地址

bot = Bot(token=TELE_TOKEN)

def get_coin_list():
    url = f"{BASE_URL}/coin/list"
    r = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"})
    r.raise_for_status()
    return r.json()

def get_fundflow(coin_type):
    url = f"{BASE_URL}/kline/indicator"
    params = {"coinType": coin_type, "indicator_key": "fundflow"}
    r = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"}, params=params)
    r.raise_for_status()
    data = r.json()
    return data[-1]["value"] if data else 0

def fetch_and_send():
    coins = get_coin_list()
    results = []
    for coin in coins[:200]:
        try:
            value = get_fundflow(coin["key"])
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

    bot.send_message(chat_id=CHAT_ID, text=msg)

if __name__ == "__main__":
    while True:
        fetch_and_send()
        time.sleep(900)  # 每15分钟执行一次
