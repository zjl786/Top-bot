import os
import requests
import time
from telegram import Bot
from dotenv import load_dotenv

# 载入环境变量
load_dotenv()
CMC_API_KEY = os.getenv("CMC_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=BOT_TOKEN)

def fetch_top100():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {
        "start": 1,
        "limit": 100,   # 抓取前100个
        "convert": "USD"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        print("请求出错:", e)
        return []

def format_message(data):
    # 这里只能用 CMC 提供的字段
    # CMC 没有“资金净流入”，只能用成交额变化代替
    sorted_data = sorted(
        data,
        key=lambda x: x["quote"]["USD"]["volume_24h"],
        reverse=True
    )[:20]

    msg = "⏰ 24小时成交额 TOP20 (USD)\n"
    for i, coin in enumerate(sorted_data, 1):
        name = coin["name"]
        symbol = coin["symbol"]
        volume = coin["quote"]["USD"]["volume_24h"]
        msg += f"{i}. {name} ({symbol}) ${volume:,.2f}\n"
    return msg

def main():
    while True:
        data = fetch_top100()
        if data:
            msg = format_message(data)
            try:
                bot.send_message(chat_id=CHAT_ID, text=msg)
                print("已发送 Telegram 消息")
            except Exception as e:
                print("发送消息失败:", e)
        else:
            print("未获取到数据")

        time.sleep(3600)  # 每1小时运行一次

if __name__ == "__main__":
    main()
