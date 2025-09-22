import os
import asyncio
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

CMC_API_KEY = os.getenv("CMC_API_KEY")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELE_TOKEN)
HEADERS = {"X-CMC_PRO_API_KEY": CMC_API_KEY}

# 保存上一次价格，用于计算资金流
previous_prices = {}

async def fetch_top100():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    params = {
        "start": 1,
        "limit": 100,
        "convert": "USD"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            data = await resp.json()
            return data.get("data", [])

def calculate_fundflow(data):
    """
    计算资金流入流出 = 成交量 * 价格变化
    """
    global previous_prices
    flows = []
    for coin in data:
        symbol = coin["symbol"]
        price = coin["quote"]["USD"]["price"]
        volume_24h = coin["quote"]["USD"]["volume_24h"]
        prev_price = previous_prices.get(symbol, price)
        # 简单估算资金流 = 成交量 * 价格变化
        fundflow = volume_24h * (price - prev_price) / prev_price
        previous_prices[symbol] = price
        flows.append({"name": symbol, "fundflow": fundflow})
    return flows

async def send_telegram(msg):
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def main_loop():
    while True:
        try:
            data = await fetch_top100()
            flows = calculate_fundflow(data)
            inflow = sorted([c for c in flows if c["fundflow"] > 0], key=lambda x: x["fundflow"], reverse=True)[:20]
            outflow = sorted([c for c in flows if c["fundflow"] < 0], key=lambda x: x["fundflow"])[:20]

            msg = f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC 资金净流入 TOP20\n"
            for i, c in enumerate(inflow, 1):
                msg += f"{i}. {c['name']} +${c['fundflow']:,.0f}\n"

            msg += f"\n⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC 资金净流出 TOP20\n"
            for i, c in enumerate(outflow, 1):
                msg += f"{i}. {c['name']} -${abs(c['fundflow']):,.0f}\n"

            await send_telegram(msg)
            print("已发送 Telegram 消息")
        except Exception as e:
            print("出错:", e)

        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
