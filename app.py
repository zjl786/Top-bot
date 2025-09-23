import requests
import time
import schedule
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

CMC_API_KEY = os.getenv("CMC_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def fetch_cmc_data():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"limit": 500, "convert": "USD"}
    r = requests.get(url, headers=headers, params=params)
    return {x["symbol"]: {
                "price": x["quote"]["USD"]["price"],
                "volume": x["quote"]["USD"]["volume_24h"]
            } for x in r.json()["data"]}

previous_data = {}

def send_telegram(message):
    resp = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        params={"chat_id": TELEGRAM_CHAT_ID, "text": message}
    )
    print("Telegram API 返回:", resp.status_code, resp.text)  # 打印返回值，方便调试

# ✅ 调试：第一次运行就发送测试消息
send_telegram("📢 Bot 调试消息：已启动，开始抓取行情！")

def job():
    global previous_data
    current_data = fetch_cmc_data()

    # 第一次运行后更新 previous_data，不再重复发送初始化消息
    if not previous_data:
        previous_data = current_data
        return

    changes = []
    for symbol in current_data:
        if symbol in previous_data:
            price_now = current_data[symbol]["price"]
            price_old = previous_data[symbol]["price"]
            vol_now = current_data[symbol]["volume"]
            vol_old = previous_data[symbol]["volume"]

            price_change_pct = (price_now - price_old) / price_old * 100 if price_old else 0
            delta_vol = vol_now - vol_old
            vol_per_hour = vol_old / 24 if vol_old else 0
            vol_change_pct = (delta_vol / vol_per_hour * 100) if vol_per_hour > 0 else 0

            changes.append((symbol, vol_change_pct, price_change_pct, delta_vol))

    top_volume = sorted(changes, key=lambda x: abs(x[1]), reverse=True)[:100]
    top_gainers = sorted(top_volume, key=lambda x: x[2], reverse=True)[:20]
    top_losers = sorted(top_volume, key=lambda x: x[2])[:20]

    message = "📊 1小时成交量&价格统计\n\n"
    message += "🚀 涨幅Top20:\n"
    for s, v_pct, p_pct, dv in top_gainers:
        message += f"{s}: 价格 {p_pct:.2f}% | 成交量 {v_pct:.1f}% (ΔVol {dv/1e6:.2f}M)\n"
    message += "\n📉 跌幅Top20:\n"
    for s, v_pct, p_pct, dv in top_losers:
        message += f"{s}: 价格 {p_pct:.2f}% | 成交量 {v_pct:.1f}% (ΔVol {dv/1e6:.2f}M)\n"

    send_telegram(message)
    previous_data = current_data

# 每小时执行一次
schedule.every().hour.do(job)

print("Bot 已启动，等待执行...")
while True:
    schedule.run_pending()
    time.sleep(1)
