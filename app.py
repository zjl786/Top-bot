import asyncio
import aiohttp
import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=BOT_TOKEN)

STABLECOINS = {"usdt", "usdc", "fdusd", "usde"}
TOP_N = 500

# 交易所公共API接口
EXCHANGES = {
    "binance": {
        "spot": "https://api.binance.com/api/v3/ticker/24hr",
        "futures": "https://fapi.binance.com/fapi/v1/ticker/24hr"
    },
    "okx": {
        "spot": "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
        "futures": "https://www.okx.com/api/v5/market/tickers?instType=FUTURES"
    },
    "bybit": {
        "spot": "https://api.bybit.com/v2/public/tickers?category=spot",
        "futures": "https://api.bybit.com/v2/public/tickers?category=linear&symbol=all"
    },
    "bitget": {
        "spot": "https://api.bitget.com/api/spot/v1/market/tickers",
        "futures": "https://api.bitget.com/api/mix/v1/market/tickers"
    },
    "gate": {
        "spot": "https://api.gateio.ws/api2/1/tickers",
        "futures": "https://api.gateio.ws/api2/1/futures/tickers"
    },
    "huobi": {
        "spot": "https://api.huobi.pro/market/tickers",
        "futures": "https://api.hbdm.com/market/tickers"
    }
}

def format_amount(amount):
    amount = float(amount)
    if abs(amount) >= 1_000_000_000:
        return f"{amount/1_000_000_000:.2f}B"
    elif abs(amount) >= 1_000_000:
        return f"{amount/1_000_000:.2f}M"
    elif abs(amount) >= 1_000:
        return f"{amount/1_000:.2f}k"
    return f"{amount:.2f}"

async def fetch(session, url, params=None):
    try:
        async with session.get(url, params=params, timeout=15) as resp:
            return await resp.json()
    except Exception as e:
        print(f"请求出错: {e}")
        return None

def parse_data(exchange, data):
    results = []
    if not data:
        return results
    try:
        if exchange == "binance":
            for item in data:
                symbol = item["symbol"].lower()
                if any(stable in symbol for stable in STABLECOINS):
                    continue
                volume = float(item.get("quoteVolume", 0))
                results.append((symbol, volume))
        elif exchange == "okx":
            for item in data.get("data", []):
                symbol = item["instId"].split("-")[0].lower()
                if symbol in STABLECOINS:
                    continue
                volume = float(item.get("volCcy24h", 0))
                results.append((symbol, volume))
        elif exchange == "bybit":
            for item in data.get("result", []):
                symbol = item["symbol"].lower()
                if any(stable in symbol for stable in STABLECOINS):
                    continue
                volume = float(item.get("quote_volume", 0))
                results.append((symbol, volume))
        elif exchange == "bitget":
            for item in data.get("data", []):
                symbol = item["symbol"].lower()
                if any(stable in symbol for stable in STABLECOINS):
                    continue
                volume = float(item.get("quoteVolume", 0))
                results.append((symbol, volume))
        elif exchange == "gate":
            for symbol, info in data.items():
                if any(stable in symbol.lower() for stable in STABLECOINS):
                    continue
                volume = float(info.get("quoteVolume", 0))
                results.append((symbol.lower(), volume))
        elif exchange == "huobi":
            for item in data.get("data", []):
                symbol = item["symbol"].lower()
                if any(stable in symbol for stable in STABLECOINS):
                    continue
                volume = float(item.get("quote_volume", 0))
                results.append((symbol, volume))
    except Exception as e:
        print(f"{exchange}解析出错: {e}")
    return results

async def fetch_all():
    results = []
    async with aiohttp.ClientSession() as session:
        for exch, urls in EXCHANGES.items():
            for market_type, url in urls.items():
                data = await fetch(session, url)
                tickers = parse_data(exch, data)
                results.extend(tickers)
    # 去重、取前 TOP_N
    seen = set()
    filtered = []
    for symbol, val in sorted(results, key=lambda x: x[1], reverse=True):
        if symbol in seen:
            continue
        seen.add(symbol)
        filtered.append((symbol, val))
        if len(filtered) >= TOP_N:
            break
    return filtered

async def fetch_and_send():
    coins = await fetch_all()
    if not coins:
        print("未获取到数据")
        return
    inflow = sorted([c for c in coins if c[1] > 0], key=lambda x: x[1], reverse=True)[:20]
    outflow = sorted([c for c in coins if c[1] < 0], key=lambda x: x[1])[:20]

    msg = "⏰ 资金净流入 TOP20\n"
    for i, (symbol, val) in enumerate(inflow, 1):
        msg += f"{i}. {symbol.upper()} +${format_amount(val)}\n"

    msg += "\n⏰ 资金净流出 TOP20\n"
    for i, (symbol, val) in enumerate(outflow, 1):
        msg += f"{i}. {symbol.upper()} -${format_amount(abs(val))}\n"

    await bot.send_message(chat_id=CHAT_ID, text=msg)
    print("已发送 Telegram 消息")

async def main_loop():
    while True:
        await fetch_and_send()
        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
