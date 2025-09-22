import os
import asyncio
import aiohttp
from telegram import Bot
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELE_TOKEN)

EXCLUDE_STABLES = ["usdt", "usdc", "fdusd", "usde"]

# 示例交易所接口配置
EXCHANGES = {
    "binance": {"spot_url": "https://api.binance.com/api/v3/ticker/24hr"},
    "okx": {"spot_url": "https://www.okx.com/api/v5/market/tickers?instType=SPOT"},
    # 其他交易所...
}

async def fetch_exchange(session, name, urls):
    results = []
    try:
        for market_type, url in urls.items():
            async with session.get(url) as resp:
                data = await resp.json()
                # 处理不同交易所的数据结构
                for item in data.get("data", data):
                    symbol = item.get("symbol") or item.get("instId")
                    price = float(item.get("quoteVolume") or item.get("quoteVolume24h") or 0)
                    base = symbol.lower().replace("usdt", "")
                    if base in EXCLUDE_STABLES:
                        continue
                    timestamp = item.get("timestamp") or item.get("closeTime") or int(datetime.utcnow().timestamp()*1000)
                    results.append({
                        "exchange": name,
                        "symbol": base.upper(),
                        "volume": price,
                        "timestamp": timestamp
                    })
    except Exception as e:
        print(f"{name}请求出错: {e}")
    return results

async def fetch_all():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_exchange(session, name, urls) for name, urls in EXCHANGES.items()]
        all_results = await asyncio.gather(*tasks)
        # 合并所有交易所结果
        merged = [item for sublist in all_results for item in sublist]
        # 按资金流量排序，取 TOP20
        inflow = sorted([c for c in merged if c["volume"] > 0], key=lambda x: x["volume"], reverse=True)[:20]
        outflow = sorted([c for c in merged if c["volume"] < 0], key=lambda x: x["volume"])[:20]
        return inflow, outflow

async def send_to_telegram():
    inflow, outflow = await fetch_all()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    msg = f"⏰ 资金净流 TOP20 ({now})\n\n⏫ 流入 TOP20\n"
    for i, c in enumerate(inflow, 1):
        vol = c["volume"]
        # 用k/M/B单位展示
        if vol >= 1e9:
            vol_str = f"${vol/1e9:.2f}B"
        elif vol >= 1e6:
            vol_str = f"${vol/1e6:.2f}M"
        elif vol >= 1e3:
            vol_str = f"${vol/1e3:.2f}K"
        else:
            vol_str = f"${vol:.2f}"
        msg += f"{i}. {c['symbol']} ({c['exchange']}) {vol_str}\n"

    msg += "\n⏬ 流出 TOP20\n"
    for i, c in enumerate(outflow, 1):
        vol = -c["volume"]
        if vol >= 1e9:
            vol_str = f"${vol/1e9:.2f}B"
        elif vol >= 1e6:
            vol_str = f"${vol/1e6:.2f}M"
        elif vol >= 1e3:
            vol_str = f"${vol/1e3:.2f}K"
        else:
            vol_str = f"${vol:.2f}"
        msg += f"{i}. {c['symbol']} ({c['exchange']}) {vol_str}\n"

    # 发送消息
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def main_loop():
    while True:
        try:
            await send_to_telegram()
        except Exception as e:
            print("发送出错:", e)
        await asyncio.sleep(3600)  # 每1小时执行一次

if __name__ == "__main__":
    asyncio.run(main_loop())
