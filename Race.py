import os
import asyncio
import json
import requests
from playwright.async_api import async_playwright

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
URL = "https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=ch"
ODDS_FILE = "last_odds.json"
ENTRIES_FILE = "today_entries.json"

def send_tg(msg):
    if TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        current_odds = {}
        race_no = "1"
        
        try:
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            
            # 獲取場次
            try:
                race_text = await page.locator(".raceNoTab.active").inner_text()
                race_no = "".join(filter(str.isdigit, race_text))
            except: pass

            # 抓取賠率單元格
            odds_cells = await page.locator(".win_odds").all()
            for i, cell in enumerate(odds_cells):
                val = (await cell.inner_text()).strip()
                if val.replace('.', '').isdigit():
                    current_odds[str(i+1)] = float(val)
        finally:
            await browser.close()

    if not current_odds: return

    # 載入數據
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        with open(ODDS_FILE, 'r') as f: last_odds = json.load(f)

    entries = {}
    if os.path.exists(ENTRIES_FILE):
        with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
            entries = json.load(f).get('entries', {})

    # 比對賠率變動
    for no, odds in current_odds.items():
        if no in last_odds:
            old = last_odds[no]
            # 跌幅超過 15% 觸發報警
            if old > odds and (old - odds) / old >= 0.15:
                name = entries.get(no, {}).get('name', f'馬匹 {no}')
                # 🏇 依照你要求的格式輸出
                report = (
                    f"🏇 *落飛警報：第 {race_no} 場*\n"
                    f"🎯 *心水推薦*：{no}號 {name}\n"
                    f"⚡ *賠率變動*：{old} 📉 *{odds}*\n"
                    f"📊 *狀態*：發現大戶資金流入！"
                )
                send_tg(report)

    # 儲存本次賠率供下次比對
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
