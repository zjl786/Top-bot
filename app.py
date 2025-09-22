import asyncio
import aiohttp
import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=BOT_TOKEN)

# 需要排除的稳定币
STABLECOINS = {"USDT", "USDC", "FDUSD", "USDE", "BUSD", "DAI", "TUSD"}

# 格式化资金金额
def format_amount(value):
    if value >= 1e9:
        return f"${value/1e9:,.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:,.2f}M"
    elif value >= 1e3:
        return f"${value/1e3:,.2f}K"
    else:
        return f"${value:,.2f}"

# 示例交易所 API 地址（现货+合约）
EXCHANGES = {
    "binance": {
        "spot": "https://api.binance.com/api/v3/ticker/24hr",
        "futures": "https://fapi.binance.com/fapi/v1/ticker/24hr"
    },
    "okx": {
        "spot": "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
        "futures": "https://www.okx.com/api/v5/market/tickers?instType=SWAP"
    },
    "bybit": {
        "spot": "https://api.bybit.com/spot/v1/symbols",
        "futures": "https://api.bybit.com/v2/public/tickers?category=linear"
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

async def fetch_exchange(session, url):
    try:
        async with session.get(url, timeout=15) as resp:
            if resp.status != 200:
                print(f"请求出错: {resp.status}, url={url}")
                return []
            data = await resp.json()
            # 解析各交易所格式，返回统一格式列表 [{'symbol': 'BTC', 'amount': 1234567}]
            result = []
            # Binance Spot/Futures
            if "binance" in url:
                for item in data[:500]:
                    symbol = item.get("symbol", "")
                    if any(stable in symbol for stable in STABLECOINS):
                        continue
                    quoteVolume = float(item.get("quoteVolume", 0))
                    result.append({"symbol": symbol.replace("USDT", ""), "amount": quoteVolume})
            # OKX Spot/Futures
            elif "okx" in url:
                items = data.get("data", [])
                for item in items[:500]:
                    symbol = item.get("instId", "")
                    if any(stable in symbol for stable in STABLECOINS):
                        continue
                    volume = float(item.get("volCcy24h", 0)) * float(item.get("last", 0))
                    result.append({"symbol": symbol.replace("-USDT", ""), "amount": volume})
            # 其他交易所可按类似逻辑解析
            # TODO: 添加 Bybit, Bitget, Gate, Huobi 数据解析
            return result
    except Exception as e:
        print(f"{url} 解析出错: {e}")
        return []

async def fetch_top_coins():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for ex, urls in EXCHANGES.items():
            for t, url in urls.items():
                tasks.append(fetch_exchange(session, url))
        results = await asyncio.gather(*tasks)
        # 扁平化列表
        all_coins = [coin for sublist in results for coin in sublist]
        # 去重合并同一symbol的资金
        coin_map = {}
        for c in all_coins:
            symbol = c["symbol"]
            coin_map[symbol] = coin_map.get(symbol, 0) + c["amount"]
        # 排序
        sorted_coins = sorted(coin_map.items(), key=lambda x: x[1], reverse=True)
        inflow = [{"symbol": s, "amount": a} for s, a in sorted_coins[:20]]
        outflow = [{"symbol": s, "amount": a} for s, a in sorted_coins[-20:]]
        return inflow, outflow

async def fetch_and_send():
    inflow, outflow = await fetch_top_coins()
    msg = "⏰ 资金净流入 TOP20\n"
    for i, c in enumerate(inflow, 1):
        msg += f"{i}. {c['symbol'].upper()} {format_amount(c['amount'])}\n"

    msg += "\n⏰ 资金净流出 TOP20\n"
    for i, c in enumerate(outflow, 1):
        msg += f"{i}. {c['symbol'].upper()} {format_amount(c['amount'])}\n"

    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        print("已发送 Telegram 消息")
    except Exception as e:
        print("发送失败:", e)

async def main_loop():
    while True:
        await fetch_and_send()
        await asyncio.sleep(3600)  # 每小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
