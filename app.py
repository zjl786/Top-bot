import os
import aiohttp
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

CMC_API_KEY = os.getenv("CMC_API_KEY")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://pro-api.coinmarketcap.com/v1"

bot = Bot(token=TELE_TOKEN)

# 获取前100代币市场数据
async def get_top_100():
    url = f"{BASE_URL}/cryptocurrency/listings/latest"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"start": 1, "limit": 100, "convert": "USD"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                print("请求失败:", await resp.text())
                return []
            data = await resp.json()
            return data.get("data", [])

# 处理数据并发送消息
async def fetch_and_send():
    coins = await get_top_100()
    if not coins:
        print("未获取到数据")
        return

    results = []
    for coin in coins:
        try:
            name = coin["name"]
            vol_change = coin["quote"]["USD"]["volume_change_24h"]  # 24小时成交量变化百分比
            volume = coin["quote"]["USD"]["volume_24h"]  # 24小时成交量(USD)
            inflow_value = volume * (vol_change / 100)  # 近似流入/流出金额
            results.append((name, inflow_value))
        except KeyError:
            continue

    # 排序
    inflow = sorted([c for c in results if c[1] > 0], key=lambda x: x[1], reverse=True)[:20]
    outflow = sorted([c for c in results if c[1] < 0], key=lambda x: x[1])[:20]

    msg = "⏰ 资金净流入 TOP20 (估算资金USD)\n"
    for i, (name, val) in enumerate(inflow, 1):
        msg += f"{i}. {name} +${val:,.2f}\n"

    msg += "\n⏰ 资金净流出 TOP20 (估算资金USD)\n"
    for i, (name, val) in enumerate(outflow, 1):
        msg += f"{i}. {name} ${val:,.2f}\n"

    # ✅ 异步调用必须 await
    await bot.send_message(chat_id=CHAT_ID, text=msg)

# 主循环
async def main_loop():
    while True:
        try:
            await fetch_and_send()
            print("已发送 Telegram 消息")
        except Exception as e:
            print("出错:", e)
        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
