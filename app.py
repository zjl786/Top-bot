import os
import asyncio
import aiohttp
from telegram import Bot
from dotenv import load_dotenv
from operator import itemgetter

load_dotenv()

CMC_API_KEY = os.getenv("CMC_API_KEY")  # CoinMarketCap API Key
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TOP_N_COINS = 100  # 前100币种
TOP_N_RESULT = 20  # 流入/流出TOP20

bot = Bot(token=TELE_TOKEN)

CMC_BASE_URL = "https://pro-api.coinmarketcap.com/v1"

HEADERS = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": CMC_API_KEY
}

async def fetch_top_coins():
    """获取前N个币种信息"""
    url = f"{CMC_BASE_URL}/cryptocurrency/listings/latest"
    params = {
        "start": "1",
        "limit": TOP_N_COINS,
        "convert": "USD"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            data = await resp.json()
            return data["data"]

async def fetch_1h_quotes(coin_id):
    """获取币种1小时前的价格和成交量"""
    url = f"{CMC_BASE_URL}/cryptocurrency/quotes/historical"
    params = {
        "id": coin_id,
        "time_start": "1 hour ago UTC",
        "interval": "1h",
        "convert": "USD"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            data = await resp.json()
            return data

def calc_fundflow(current, previous):
    """
    粗略计算资金净流入：
    (当前价格 - 1小时前价格) * 当前成交量
    """
    price_diff = current["price"] - previous["price"]
    volume = current["quote"]["USD"]["volume_24h"]
    return price_diff * volume

async def generate_report():
    coins = await fetch_top_coins()
    results = []

    for coin in coins:
        try:
            coin_id = coin["id"]
            # 这里示例不调用历史接口，直接用当前24h数据粗略估算
            fundflow = coin["quote"]["USD"]["volume_24h"] * coin["quote"]["USD"]["percent_change_1h"] / 100
            results.append((coin["name"], fundflow))
        except Exception as e:
            continue

    inflow = sorted([c for c in results if c[1] > 0], key=itemgetter(1), reverse=True)[:TOP_N_RESULT]
    outflow = sorted([c for c in results if c[1] < 0], key=itemgetter(1))[:TOP_N_RESULT]

    msg = "⏰ 资金净流入 TOP20 (近1小时)\n"
    for i, (name, val) in enumerate(inflow, 1):
        msg += f"{i}. {name} +{val:,.2f} USD\n"

    msg += "\n⏰ 资金净流出 TOP20 (近1小时)\n"
    for i, (name, val) in enumerate(outflow, 1):
        msg += f"{i}. {name} {val:,.2f} USD\n"

    return msg

async def main_loop():
    while True:
        try:
            report = await generate_report()
            await bot.send_message(chat_id=CHAT_ID, text=report)
            print("已发送 Telegram 消息")
        except Exception as e:
            print("出错:", e)
        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
