import os
import asyncio
import aiohttp
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELE_TOKEN)

# 排除稳定币
STABLECOINS = {"USDT", "USDC", "FDUSD", "USDE", "BUSD", "DAI", "TUSD", "USDP"}

# 数字格式化
def format_number(num):
    if abs(num) >= 1_000_000_000:
        return f"{num/1_000_000_000:.2f}B"
    elif abs(num) >= 1_000_000:
        return f"{num/1_000_000:.2f}M"
    elif abs(num) >= 1_000:
        return f"{num/1_000:.2f}K"
    else:
        return f"{num:.2f}"

# 交易所配置
EXCHANGES = [
    {
        "name": "binance",
        "spot_url": "https://api.binance.com/api/v3/ticker/24hr",
        "future_url": "https://fapi.binance.com/fapi/v1/ticker/24hr",
        "parser": lambda data: [
            {"symbol": d["symbol"], "volume": float(d["quoteVolume"])} for d in data
        ]
    },
    {
        "name": "okx",
        "spot_url": "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
        "future_url": "https://www.okx.com/api/v5/market/tickers?instType=FUTURES",
        "parser": lambda data: [
            {"symbol": d["instId"], "volume": float(d["volCcy"])} for d in data["data"]
        ]
    },
    {
        "name": "huobi",
        "spot_url": "https://api.huobi.pro/market/tickers",
        "future_url": "https://api.hbdm.com/market/tickers",
        "parser": lambda data: [
            {"symbol": d["symbol"], "volume": float(d.get("quoteVol", 0))} for d in data
        ]
    },
    {
        "name": "bitget",
        "spot_url": "https://api.bitget.com/api/spot/v1/market/tickers",
        "future_url": "https://api.bitget.com/api/mix/v1/market/tickers",
        "parser": lambda data: [
            {"symbol": d["symbol"], "volume": float(d.get("quoteVol", 0))} for d in data.get("data", [])
        ]
    },
    {
        "name": "bybit",
        "spot_url": "https://api.bybit.com/spot/v1/symbols",
        "future_url": "https://api.bybit.com/v2/public/tickers?category=linear",
        "parser": lambda data: [
            {"symbol": d["symbol"], "volume": float(d.get("quote_volume", 0))}
            for d in data.get("result", [])
        ]
    },
    {
        "name": "gate",
        "spot_url": "https://api.gateio.ws/api2/1/tickers",
        "future_url": "https://api.gateio.ws/api2/1/futures/tickers",
        "parser": lambda data: [
            {"symbol": k, "volume": float(v["quoteVolume"])} for k, v in data.items()
            if "quoteVolume" in v
        ]
    },
]

async def fetch_exchange(session, url, parser):
    try:
        async with session.get(url) as resp:
            data = await resp.json()
            return parser(data)
    except Exception:
        return []

async def fetch_all():
    results = []
    async with aiohttp.ClientSession() as session:
        for ex in EXCHANGES:
            spot = await fetch_exchange(session, ex["spot_url"], ex["parser"])
            future = await fetch_exchange(session, ex["future_url"], ex["parser"])
            results.extend(spot)
            results.extend(future)
    # 排除稳定币
    results = [r for r in results if not any(s in r["symbol"].upper() for s in STABLECOINS)]
    # 按 volume 排序，取前500
    results.sort(key=lambda x: x["volume"], reverse=True)
    return results[:500]

async def main_loop():
    while True:
        coins = await fetch_all()
        inflow_top = coins[:20]
        outflow_top = coins[-20:]

        msg = "⏰ 资金净流入 TOP20 (USDT)\n"
        for i, c in enumerate(inflow_top, 1):
            msg += f"{i}. {c['symbol']} +${format_number(c['volume'])}\n"

        msg += "\n⏰ 资金净流出 TOP20 (USDT)\n"
        for i, c in enumerate(outflow_top, 1):
            msg += f"{i}. {c['symbol']} -${format_number(c['volume'])}\n"

        try:
            await bot.send_message(chat_id=CHAT_ID, text=msg)
        except Exception as e:
            print("发送 Telegram 出错:", e)

        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
