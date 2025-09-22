import asyncio
import aiohttp
from datetime import datetime
from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=BOT_TOKEN)

STABLECOINS = ["usdt", "usdc", "fdusd", "usde"]

async def fetch_binance(session):
    url = "https://api.binance.com/api/v3/ticker/24hr"
    results = []
    try:
        async with session.get(url) as resp:
            data = await resp.json()
            for item in data:
                symbol = item.get("symbol", "").lower()
                if any(stable in symbol for stable in STABLECOINS):
                    continue
                volume = float(item.get("quoteVolume", 0))
                results.append({"exchange": "binance", "symbol": symbol, "volume": volume})
    except Exception as e:
        print("binance请求出错:", e)
    return results

async def fetch_okx(session):
    urls = {
        "spot": "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
        "futures": "https://www.okx.com/api/v5/market/tickers?instType=FUTURES"
    }
    results = []
    try:
        for instype, url in urls.items():
            async with session.get(url) as resp:
                data = await resp.json()
                for item in data.get("data", []):
                    symbol = item.get("instId", "").lower()
                    if any(stable in symbol for stable in STABLECOINS):
                        continue
                    volume = float(item.get("volCcy", 0)) * float(item.get("last", 1))
                    results.append({"exchange": "okx", "symbol": symbol, "volume": volume})
    except Exception as e:
        print("okx请求出错:", e)
    return results

async def fetch_bybit(session):
    urls = [
        "https://api.bybit.com/v2/public/tickers?category=spot",
        "https://api.bybit.com/v2/public/tickers?category=linear"
    ]
    results = []
    try:
        for url in urls:
            async with session.get(url) as resp:
                data = await resp.json()
                for item in data.get("result", []):
                    symbol = item.get("symbol", "").lower()
                    if any(stable in symbol for stable in STABLECOINS):
                        continue
                    volume = float(item.get("quote_volume", 0))
                    results.append({"exchange": "bybit", "symbol": symbol, "volume": volume})
    except Exception as e:
        print("bybit请求出错:", e)
    return results

async def fetch_bitget(session):
    urls = [
        "https://api.bitget.com/api/spot/v1/market/tickers",
        "https://api.bitget.com/api/mix/v1/market/tickers"
    ]
    results = []
    try:
        for url in urls:
            async with session.get(url) as resp:
                data = await resp.json()
                for item in data.get("data", []):
                    symbol = item.get("symbol", "").lower()
                    if any(stable in symbol for stable in STABLECOINS):
                        continue
                    volume = float(item.get("quoteVol", 0))
                    results.append({"exchange": "bitget", "symbol": symbol, "volume": volume})
    except Exception as e:
        print("bitget请求出错:", e)
    return results

async def fetch_gate(session):
    url = "https://api.gateio.ws/api2/1/tickers"
    results = []
    try:
        async with session.get(url) as resp:
            data = await resp.json()
            for k, v in data.items():
                symbol = k.lower()
                if any(stable in symbol for stable in STABLECOINS):
                    continue
                volume = float(v.get("quoteVolume", 0))
                results.append({"exchange": "gate", "symbol": symbol, "volume": volume})
    except Exception as e:
        print("gate解析出错:", e)
    return results

async def fetch_huobi(session):
    urls = [
        "https://api.huobi.pro/market/tickers",
        "https://api.hbdm.com/linear-swap-api/v1/swap_tick"
    ]
    results = []
    try:
        for url in urls:
            async with session.get(url) as resp:
                data = await resp.json()
                for item in data.get("data", []):
                    symbol = item.get("symbol", "").lower()
                    if any(stable in symbol for stable in STABLECOINS):
                        continue
                    volume = float(item.get("quoteVolume", 0))
                    results.append({"exchange": "huobi", "symbol": symbol, "volume": volume})
    except Exception as e:
        print("huobi请求出错:", e)
    return results

async def fetch_all():
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_binance(session),
            fetch_okx(session),
            fetch_bybit(session),
            fetch_bitget(session),
            fetch_gate(session),
            fetch_huobi(session)
        ]
        results = await asyncio.gather(*tasks)
        # 合并所有交易所数据
        all_data = [item for sublist in results for item in sublist]
        return all_data

def format_volume(v):
    if v >= 1e9:
        return f"${v/1e9:.2f}B"
    if v >= 1e6:
        return f"${v/1e6:.2f}M"
    if v >= 1e3:
        return f"${v/1e3:.2f}K"
    return f"${v:.2f}"

async def main_loop():
    while True:
        data = await fetch_all()
        if not data:
            print("未获取到数据")
            await asyncio.sleep(3600)
            continue
        # 按流入量排序，取前20
        inflow = sorted(data, key=lambda x: x["volume"], reverse=True)[:20]
        # 按流出量排序，取前20（最小 volume）
        outflow = sorted(data, key=lambda x: x["volume"])[:20]

        msg = "⏰ 资金净流入 TOP20 (USDT)\n"
        for i, item in enumerate(inflow, 1):
            msg += f"{i}. {item['symbol']} {format_volume(item['volume'])}\n"

        msg += "\n⏰ 资金净流出 TOP20 (USDT)\n"
        for i, item in enumerate(outflow, 1):
            msg += f"{i}. {item['symbol']} {format_volume(item['volume'])}\n"

        await bot.send_message(chat_id=CHAT_ID, text=msg)
        print(f"已发送 Telegram 消息, 时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
