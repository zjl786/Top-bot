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

BASE_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
STABLECOINS = {"USDT", "USDC", "FDUSD", "DAI", "BUSD", "TUSD", "UST", "USDP", "GUSD", "PAX"}

HEADERS = {"X-CMC_PRO_API_KEY": CMC_API_KEY}

def format_amount(amount: float) -> str:
    """将数值转换为 k/M/B 格式"""
    abs_amount = abs(amount)
    if abs_amount >= 1_000_000_000:
        return f"${amount/1_000_000_000:.2f}B"
    elif abs_amount >= 1_000_000:
        return f"${amount/1_000_000:.2f}M"
    elif abs_amount >= 1_000:
        return f"${amount/1_000:.2f}k"
    else:
        return f"${amount:.2f}"

async def fetch_top_coins(limit=500):
    params = {
        "start": "1",
        "limit": str(limit),
        "convert": "USD"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, headers=HEADERS, params=params) as resp:
            if resp.status != 200:
                print("未获取到数据", await resp.text())
                return []
            data = await resp.json()
            return data.get("data", [])

def get_fundflow(coin):
    """计算估算资金流入：按1小时价格变动 * 市值"""
    # 注意：CMC API 免费计划仅提供24h涨跌，无法精确获取1小时资金流动
    # 这里用24h % 变化和市值简单估算
    price_change = coin.get("quote", {}).get("USD", {}).get("percent_change_24h", 0)
    market_cap = coin.get("quote", {}).get("USD", {}).get("market_cap", 0)
    return market_cap * price_change / 100

async def fetch_and_send():
    coins = await fetch_top_coins()
    results = []

    for coin in coins:
        symbol = coin.get("symbol", "")
        if symbol.upper() in STABLECOINS:
            continue
        value = get_fundflow(coin)
        results.append((symbol, value))

    inflow = sorted([c for c in results if c[1] > 0], key=lambda x: x[1], reverse=True)[:20]
    outflow = sorted([c for c in results if c[1] < 0], key=lambda x: x[1])[:20]

    msg = "⏰ 资金净流入 TOP20\n"
    for i, (name, val) in enumerate(inflow, 1):
        msg += f"{i}. {name} +{format_amount(val)}\n"

    msg += "\n⏰ 资金净流出 TOP20\n"
    for i, (name, val) in enumerate(outflow, 1):
        msg += f"{i}. {name} {format_amount(val)}\n"

    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        print("已发送 Telegram 消息")
    except Exception as e:
        print("发送消息失败:", e)

async def main_loop():
    while True:
        await fetch_and_send()
        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
