import os
import json
import requests

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def send_tg(msg):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        print(f"Telegram 回應: {resp.status_code}")

def test_logic():
    print("🚀 開始模擬測試...")
    
    # 1. 模擬「上次」的賠率 (1號馬 10倍)
    last_odds = {"1": 10.0}
    
    # 2. 模擬「現在」的賠率 (1號馬 跌到 5.0倍)
    current_odds = {"1": 5.0}
    
    # 3. 模擬馬名數據
    entries = {"1": {"name": "測試幸運星"}}

    # 4. 比對邏輯
    for no, odds in current_odds.items():
        old = last_odds.get(no)
        if old and old > odds and (old - odds) / old >= 0.15:
            name = entries.get(no, {}).get('name', f'{no}號馬')
            report = (
                f"🔔 *【測試】大戶資金監控*\n\n"
                f"🏇 *賽目前瞻：第 1 場*\n"
                f"🎯 *精選心水*：{no}號 {name}\n"
                f"📉 *變動*：{old} ➡️ *{odds}* (跌幅 50%)\n"
                f"⚡ *提示*：模擬數據測試成功！"
            )
            send_tg(report)
            print("✅ 已發送 Telegram 通知")

if __name__ == "__main__":
    test_logic()
