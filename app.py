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
STABLECOINS = {"USDT","USDC","FDUSD","USDE"}

# 交易所及 API 配置
EXCHANGES = [
    {
        "name": "binance",
        "spot_url": "https://api.binance.com/api/v3/ticker/24hr",
        "future_url": "https://fapi.binance.com/fapi/v1/ticker/24hr",
        "spot_parser": lambda x: {"symbol": x["symbol"], "priceChange": float(x["quoteVolume"])},
        "future_parser": lambda x: {"symbol": x["symbol"], "priceChange": float(x["quoteVolume"])}
    },
    {
        "name": "okx",
        "spot_url": "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
        "future_url": "https://www.okx.com/api/v5/market/tickers?instType=SWAP",
        "spot_parser": lambda x: {"symbol": x["instId"].replace("-",""), "priceChange": float(x["volCcy24h"])},
        "future_parser": lambda x: {"symbol": x["instId"].replace("-",""), "priceChange": float(x["volCcy24h"])}
    },
    {
        "name": "bybit",
        "spot_url": "https://api.bybit.com/spot/v1/symbols",
        "future_url": "https://api.bybit.com/v2/public/tickers?category=linear",
        "spot_parser": lambda x: {"symbol": x["name"], "priceChange": float(x["quote_volume"])} if "quote_volume" in x else None,
        "future_parser": lambda x: {"symbol": x["symbol"], "priceChange": float(x["quote_volume"])} if "quote_volume" in x else None
    },
    {
        "name": "bitget",
        "spot_url": "https://api.bitget.com/api/spot/v1/market/tickers",
        "future_url": "https://api.bitget.com/api/mix/v1/market/tickers?symbol=all",
        "spot_parser": lambda x: {"symbol": x["symbol"], "priceChange": float(x["quoteVol"])} if "quoteVol" in x else None,
        "future_parser": lambda x: {"symbol": x["symbol"], "priceChange": float(x["quoteVol"])} if "quoteVol" in x else None
    },
    {
        "name": "gate",
        "spot_url": "https://api.gateio.ws/api2/1/tickers",
        "future_url": "https://api.gateio.ws/api2/1/futures/tickers",
        "spot_parser": lambda x: {"symbol": k, "priceChange": float(v["quoteVolume"])} for k,v in x.items(),
        "future_parser": lambda x: {"symbol": k, "priceChange": float(v["quoteVolume"])} for k,v in x.items()
    },
    {
        "name": "huobi",
        "spot_url": "https://api.huobi.pro/market/tickers",
        "future_url": "https://api.hbdm.com/linear-swap-api/v1/swap_market_tickers",
        "spot_parser": lambda x: {"symbol": x["symbol"], "priceChange": float(x["quoteVol"])} if "quoteVol" in x else None,
        "future_parser": lambda x: {"symbol": x["symbol"], "priceChange": float(x["quoteVol"])} if "quoteVol" in x else None
    }
]

async def fetch_exchange(session, url):
    try:
        async with session.get(url, timeout=20) as resp:
            if resp.status != 200:
                print(f"请求出错: {resp.status}, url={url}")
                return []
            data = await resp.json()
            # 对 Gate 和 OKX 需要取 data 字段
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data
    except Exception as e:
        print(f"请求出错: {e}, url={url}")
        return []

async def fetch_top_coins():
    results = []
    async with aiohttp.ClientSession() as session:
        for ex in EXCHANGES:
            for url, parser in [(ex["spot_url"], ex["spot_parser"]),
                                (ex["future_url"], ex["future_parser"])]:
                data = await fetch_exchange(session, url)
                if not data:
                    continue
                try:
                    parsed = []
                    if isinstance(data, list):
                        for c in data:
                            p = parser(c)
                            if p and not any(sc in p["symbol"] for sc in STABLECOINS):
                                parsed.append(p)
                    elif isinstance(data, dict):
                        for k,v in data.items():
                            if isinstance(parser, type(lambda:0)):
                                p = parser({k:v})
                                if p and not any(sc in p["symbol"] for sc in STABLECOINS):
                                    parsed.append(p)
                    results.extend(parsed)
                except Exception as e:
                    print(f"{ex['name']}解析出错: {e}")
    # 前500币种
    results = sorted(results, key=lambda x: x["priceChange"], reverse=True)[:500]
    return results

async def fetch_and_send():
    coins = await fetch_top_coins()
    if not coins:
        await bot.send_message(chat_id=CHAT_ID, text="未获取到数据")
        return
    inflow = sorted([c for c in coins if c["priceChange"]>0], key=lambda x:x["priceChange"], reverse=True)[:20]
    outflow = sorted([c for c in coins if c["priceChange"]<0], key=lambda x:x["priceChange"])[:20]

    def fmt(v):
        val = v["priceChange"]
        if val>=1e9:
            return f"${val/1e9:.2f}B"
        elif val>=1e6:
            return f"${val/1e6:.2f}M"
        elif val>=1e3:
            return f"${val/1e3:.2f}K"
        return f"${val:.2f}"

    msg = "⏰ 资金净流入 TOP20\n"
    for i, c in enumerate(inflow, 1):
        msg += f"{i}. {c['symbol']} {fmt(c)}\n"

    msg += "\n⏰ 资金净流出 TOP20\n"
    for i, c in enumerate(outflow, 1):
        msg += f"{i}. {c['symbol']} {fmt(c)}\n"

    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def main_loop():
    while True:
        await fetch_and_send()
        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
