import os
import requests
import time
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

# --- 配置 ---
CMC_API_KEY = os.getenv("COINMARKETCAP_API_KEY")  # CoinMarketCap API Key
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")      # Telegram Bot Token
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")           # Telegram Chat ID
bot = Bot(token=TELE_TOKEN)

# 每次抓取前1000个币种
LIMIT = 1000

# CoinMarketCap 资金流入/流出指标
def get_top_coins(limit=LIMIT):
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {
        "start": "1",
        "limit": str(limit),
        "convert": "USD"
    }

    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    data = r.json()["data"]

    # 按 24h 资金流入/流出（percent_change_24h）排序
    results = []
    for coin in data:
        change_24h = coin.get("quote", {}).get("USD", {}).get("volume_24h", 0)
        results.append((coin["name"], change_24h))

    return results

def fetch_and_send():
    coins = get_top_coins()
    # 按资金流入排序
    inflow = sorted([c for c in coins if c[1] > 0], key=lambda x: x[1], reverse=True)[:20]
    outflow = sorted([c for c in coins if c[1] < 0], key=lambda x: x[1])[:20]

    msg = "⏰ 资金净流入 TOP20\n"
    for i, (name, val) in enumerate(inflow, 1):
        msg += f"{i}. {name} +${val:,.2f}\n"

    msg += "\n⏰ 资金净流出 TOP20\n"
    for i, (name, val) in enumerate(outflow, 1):
        msg += f"{i}. {name} ${val:,.2f}\n"

    bot.send_message(chat_id=CHAT_ID, text=msg)
    print("已发送 Telegram 消息")

if __name__ == "__main__":
    while True:
        try:
            fetch_and_send()
        except Exception as e:
            print("发生错误:", e)
        time.sleep(3600)  # 每1小时执行一次
