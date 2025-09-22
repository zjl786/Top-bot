import asyncio
import aiohttp
from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELE_TOKEN)

STABLECOINS = {"USDT", "USDC", "FDUSD", "USDE"}

EXCHANGES = {
    "binance": "https://api.binance.com/api/v3/ticker/24hr",
    "okx": "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
    "huobi": "https://api.huobi.pro/market/tickers",
    "gate": "https://api.gateio.ws/api2/1/tickers",
    "bybit": "https://api.bybit.com/spot/quote/v1/ticker/24hr",
    "bitget": "https://api.bitget.com/api/spot/v1/market/tickers"
}

# 格式化大数字
def format_amount(amount):
    if amount >= 1e9:
        return f"{amount/1e9:.2f}B"
    elif amount >= 1e6:
        return f"{amount/1e6:.2f}M"
    elif amount >= 1e3:
        return f"{amount/1e3:.2f}k"
    else:
        return f"{amount:.2f}"

async def fetch_binance(session):
    results = {}
    try:
        async with session.get(EXCHANGES["binance"]) as resp:
            data = await resp.json()
            for item in data[:500]:
                symbol = item["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                coin = symbol.replace("USDT","")
                if coin in STABLECOINS:
                    continue
                results[coin] = float(item.get("quoteVolume", 0))
    except Exception as e:
        print("binance请求出错:", e)
    return results

async def fetch_okx(session):
    results = {}
    try:
        async with session.get(EXCHANGES["okx"]) as resp:
            data = await resp.json()
            for item in data.get("data", [])[:500]:
                instId = item["instId"]
                if not instId.endswith("USDT"):
                    continue
                coin = instId.replace("USDT","")
                if coin in STABLECOINS:
                    continue
                results[coin] = float(item.get("volCcy24h", 0))
    except Exception as e:
        print("okx请求出错:", e)
    return results

async def fetch_huobi(session):
    results = {}
    try:
        async with session.get(EXCHANGES["huobi"]) as resp:
            data = await resp.json()
            for item in data.get("data", [])[:500]:
                symbol = item["symbol"]
                if not symbol.endswith("usdt"):
                    continue
                coin = symbol.replace("usdt","").upper()
                if coin in STABLECOINS:
                    continue
                results[coin] = float(item.get("quote-currency-volume", 0))
    except Exception as e:
        print("huobi请求出错:", e)
    return results

async def fetch_gate(session):
    results = {}
    try:
        async with session.get(EXCHANGES["gate"]) as resp:
            data = await resp.json()
            for pair, info in list(data.items())[:500]:
                if not pair.endswith("_USDT"):
                    continue
                coin = pair.replace("_USDT","")
                if coin in STABLECOINS:
                    continue
                results[coin] = float(info.get("quoteVolume", 0))
    except Exception as e:
        print("gate请求出错:", e)
    return results

async def fetch_bybit(session):
    results = {}
    try:
        async with session.get(EXCHANGES["bybit"]) as resp:
            data = await resp.json()
            for item in data.get("result", [])[:500]:
                symbol = item["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                coin = symbol.replace("USDT","")
                if coin in STABLECOINS:
                    continue
                results[coin] = float(item.get("quoteVolume",0))
    except Exception as e:
        print("bybit请求出错:", e)
    return results

async def fetch_bitget(session):
    results = {}
    try:
        async with session.get(EXCHANGES["bitget"]) as resp:
            data = await resp.json()
            for item in data.get("data", [])[:500]:
                symbol = item["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                coin = symbol.replace("USDT","")
                if coin in STABLECOINS:
                    continue
                results[coin] = float(item.get("quoteVolume",0))
    except Exception as e:
        print("bitget请求出错:", e)
    return results

async def fetch_all():
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_binance(session),
            fetch_okx(session),
            fetch_huobi(session),
            fetch_gate(session),
            fetch_bybit(session),
            fetch_bitget(session)
        ]
        results = await asyncio.gather(*tasks)
        merged = {}
        for r in results:
            for k, v in r.items():
                merged[k] = merged.get(k,0) + v
        return merged

async def fetch_and_send():
    data = await fetch_all()
    if not data:
        print("未获取到数据")
        return

    sorted_inflow = sorted(data.items(), key=lambda x: x[1], reverse=True)[:20]
    sorted_outflow = sorted(data.items(), key=lambda x: x[1])[:20]

    msg = "⏰ 资金净流入 TOP20 (USDT)\n"
    for i, (coin, val) in enumerate(sorted_inflow,1):
        msg += f"{i}. {coin} +${format_amount(val)}\n"

    msg += "\n⏰ 资金净流出 TOP20 (USDT)\n"
    for i, (coin, val) in enumerate(sorted_outflow,1):
        msg += f"{i}. {coin} -${format_amount(val)}\n"

    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        print("已发送 Telegram 消息")
    except Exception as e:
        print("发送 Telegram 消息失败:", e)

async def main_loop():
    while True:
        await fetch_and_send()
        await asyncio.sleep(3600)  # 每小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
