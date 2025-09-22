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
STABLECOINS = {"usdt", "usdc", "fdusd", "usde"}

# 显示资金单位
def format_amount(amount):
    abs_amount = abs(amount)
    if abs_amount >= 1_000_000_000:
        return f"${amount/1_000_000_000:.2f}B"
    elif abs_amount >= 1_000_000:
        return f"${amount/1_000_000:.2f}M"
    elif abs_amount >= 1_000:
        return f"${amount/1_000:.2f}K"
    else:
        return f"${amount:.2f}"

async def fetch_binance(session):
    url = "https://api.binance.com/api/v3/ticker/24hr"
    try:
        async with session.get(url) as resp:
            data = await resp.json()
            result = {}
            for coin in data:
                symbol = coin["symbol"]
                quote_vol = float(coin["quoteVolume"])
                if symbol.endswith("USDT"):
                    base = symbol[:-4].lower()
                    if base not in STABLECOINS:
                        result[base] = quote_vol
            return result
    except Exception as e:
        print(f"binance请求出错: {e}")
        return {}

async def fetch_okx(session):
    url = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
    try:
        async with session.get(url) as resp:
            res = await resp.json()
            data = res.get("data", [])
            result = {}
            for d in data:
                symbol = d["instId"]
                vol = float(d["volCcy24h"])
                if symbol.endswith("USDT"):
                    base = symbol[:-4].lower()
                    if base not in STABLECOINS:
                        result[base] = vol
            return result
    except Exception as e:
        print(f"okx请求出错: {e}")
        return {}

async def fetch_huobi(session):
    url = "https://api.huobi.pro/market/tickers"
    try:
        async with session.get(url) as resp:
            res = await resp.json()
            data = res.get("data", [])
            result = {}
            for d in data:
                symbol = d["symbol"]
                quote_vol = float(d["quote-currency-volume"])
                if symbol.endswith("usdt"):
                    base = symbol[:-4].lower()
                    if base not in STABLECOINS:
                        result[base] = quote_vol
            return result
    except Exception as e:
        print(f"huobi请求出错: {e}")
        return {}

async def fetch_gate(session):
    url = "https://api.gateio.ws/api2/1/tickers"
    try:
        async with session.get(url) as resp:
            data = await resp.json()
            result = {}
            for k, v in data.items():
                if k.endswith("_USDT"):
                    base = k.split("_")[0].lower()
                    if base not in STABLECOINS:
                        result[base] = float(v["quoteVolume"])
            return result
    except Exception as e:
        print(f"gate解析出错: {e}")
        return {}

async def fetch_bybit(session):
    # 只抓现货USDT交易对
    url = "https://api.bybit.com/spot/quote/v1/ticker/24hr"
    try:
        async with session.get(url) as resp:
            res = await resp.json()
            result = {}
            for d in res.get("result", []):
                symbol = d["symbol"]
                quote_vol = float(d["quoteVolume"])
                if symbol.endswith("USDT"):
                    base = symbol[:-4].lower()
                    if base not in STABLECOINS:
                        result[base] = quote_vol
            return result
    except Exception as e:
        print(f"bybit请求出错: {e}")
        return {}

async def fetch_bitget(session):
    url = "https://api.bitget.com/api/spot/v1/market/tickers"
    try:
        async with session.get(url) as resp:
            res = await resp.json()
            result = {}
            for d in res.get("data", []):
                symbol = d["symbol"]
                quote_vol = float(d["quoteVol"])
                if symbol.endswith("USDT"):
                    base = symbol[:-4].lower()
                    if base not in STABLECOINS:
                        result[base] = quote_vol
            return result
    except Exception as e:
        print(f"bitget解析出错: {e}")
        return {}

async def fetch_all():
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_binance(session),
            fetch_okx(session),
            fetch_huobi(session),
            fetch_gate(session),
            fetch_bybit(session),
            fetch_bitget(session),
        ]
        results = await asyncio.gather(*tasks)
        # 合并资金流
        total = {}
        for r in results:
            for k, v in r.items():
                total[k] = total.get(k, 0) + v
        return total

async def fetch_and_send():
    data = await fetch_all()
    if not data:
        msg = "未获取到数据"
    else:
        # 按资金流排序
        sorted_inflow = sorted(data.items(), key=lambda x: x[1], reverse=True)[:20]
        sorted_outflow = sorted(data.items(), key=lambda x: x[1])[-20:]
        msg = "⏰ 资金净流入 TOP20 (USDT)\n"
        for i, (name, val) in enumerate(sorted_inflow, 1):
            msg += f"{i}. {name.upper()} {format_amount(val)}\n"
        msg += "\n⏰ 资金净流出 TOP20 (USDT)\n"
        for i, (name, val) in enumerate(sorted_outflow, 1):
            msg += f"{i}. {name.upper()} -{format_amount(val)}\n"
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def main_loop():
    while True:
        await fetch_and_send()
        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
