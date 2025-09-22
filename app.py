import os
import asyncio
import aiohttp
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

CMC_API_KEY = os.getenv("COINMARKETCAP_API_KEY")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELE_TOKEN)

HEADERS = {
    "X-CMC_PRO_API_KEY": CMC_API_KEY,
    "Accepts": "application/json"
}

async def get_top_coins(limit=100):
    url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?limit={limit}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            data = await resp.json()
            coins = data.get("data", [])
            return coins

async def fetch_and_send():
    coins = await get_top_coins(100)

    results = []
    for coin in coins:
        name = coin.get("name") or "Unknown"
        symbol = coin.get("symbol") or ""
        # 这里用 1 小时价格变化百分比代替资金流入，实际使用需要替换成真实资金流
        percent_change_1h = coin.get("quote", {}).get("USD", {}).get("percent_change_1h") or 0
        results.append((name, percent_change_1h))

    inflow = sorted([c for c in results if c[1] > 0], key=lambda x: x[1], reverse=True)[:20]
    outflow = sorted([c for c in results if c[1] < 0], key=lambda x: x[1])[:20]

    msg = "⏰ 资金净流入 TOP20 (价格涨幅%)\n"
    for i, (name, val) in enumerate(inflow, 1):
        msg += f"{i}. {name} +{val:.2f}%\n"

    msg += "\n⏰ 资金净流出 TOP20 (价格跌幅%)\n"
    for i, (name, val) in enumerate(outflow, 1):
        msg += f"{i}. {name} {val:.2f}%\n"

    # 异步发送 Telegram 消息
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def main_loop():
    while True:
        try:
            await fetch_and_send()
        except Exception as e:
            print("出错:", e)
        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
