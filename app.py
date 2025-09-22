import os
import asyncio
import aiohttp
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELE_TOKEN)

BASE_COINS_LIMIT = 500
STABLECOINS = {"USDT", "USDC", "BUSD", "DAI", "FDUSD", "TUSD", "USDP"}

EXCHANGES = {
    "binance_spot": "https://api.binance.com/api/v3/ticker/24hr",
    "binance_futures": "https://fapi.binance.com/fapi/v1/ticker/24hr",
    "okx_spot": "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
    "okx_futures": "https://www.okx.com/api/v5/market/tickers?instType=FUTURES",
    "okx_swap": "https://www.okx.com/api/v5/market/tickers?instType=SWAP",
    "bybit_spot": "https://api.bybit.com/spot/v1/symbols",
    "bybit_linear": "https://api.bybit.com/derivatives/v3/public/tickers?category=linear",
    "bybit_inverse": "https://api.bybit.com/derivatives/v3/public/tickers?category=inverse",
    "bitget_spot": "https://api.bitget.com/api/spot/v1/market/symbols",
    "bitget_futures": "https://api.bitget.com/api/mix/v1/market/tickers",
    "gate_spot": "https://api.gateio.ws/api2/1/tickers",
    "gate_futures": "https://api.gateio.ws/api/v4/futures/usdt/tickers",
    "huobi_spot": "https://api.huobi.pro/market/tickers",
    "huobi_futures": "https://api.hbdm.com/linear-swap-api/v1/swap_tickers",
}

async def fetch_json(session, url):
    try:
        async with session.get(url, timeout=10) as resp:
            return await resp.json()
    except Exception as e:
        print(f"请求出错 {url}: {e}")
        return None

def format_usd(value):
    """格式化资金数量"""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f}B"
    elif abs_value >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    elif abs_value >= 1_000:
        return f"${value/1_000:.2f}K"
    else:
        return f"${value:.2f}"

async def fetch_top_coins():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_json(session, url) for url in EXCHANGES.values()]
        results = await asyncio.gather(*tasks)

    coin_data = {}
    for data in results:
        if not data:
            continue
        # 针对不同交易所解析
        if isinstance(data, dict):
            # Gate.io 可能返回字典 {'ticker': {...}}
            items = data.get("ticker") or data.get("data") or []
            if isinstance(items, dict):
                items = items.values()
        elif isinstance(data, list):
            items = data
        else:
            continue

        for coin in items:
            # 解析 symbol/name 和 quoteVolume
            symbol = coin.get("symbol") or coin.get("instId") or coin.get("s") or coin.get("show")
            quote_volume = coin.get("quoteVolume") or coin.get("quoteVol") or coin.get("quoteVolume24h") or coin.get("quoteUsd24h") or coin.get("volumeUsd24h") or coin.get("quote") or 0
            if not symbol or any(stable in symbol.upper() for stable in STABLECOINS):
                continue
            if symbol not in coin_data:
                coin_data[symbol] = 0
            coin_data[symbol] += float(quote_volume)

    # 前 BASE_COINS_LIMIT 排序
    sorted_coins = sorted(coin_data.items(), key=lambda x: x[1], reverse=True)[:BASE_COINS_LIMIT]
    return sorted_coins

async def fetch_and_send():
    top_coins = await fetch_top_coins()
    if not top_coins:
        msg = "未获取到数据"
    else:
        inflow = top_coins[:20]
        outflow = sorted(top_coins[-20:], key=lambda x: x[1])
        msg = "⏰ 资金净流入 TOP20\n"
        for i, (symbol, val) in enumerate(inflow, 1):
            msg += f"{i}. {symbol} {format_usd(val)}\n"
        msg += "\n⏰ 资金净流出 TOP20\n"
        for i, (symbol, val) in enumerate(outflow, 1):
            msg += f"{i}. {symbol} {format_usd(val)}\n"

    await bot.send_message(chat_id=CHAT_ID, text=msg)
    print("已发送 Telegram 消息")

async def main_loop():
    while True:
        await fetch_and_send()
        await asyncio.sleep(3600)  # 每小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
