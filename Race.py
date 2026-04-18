import os
import asyncio
import json
import requests
from playwright.async_api import async_playwright

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
# 賠率頁面
URL = "https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=ch"
ODDS_FILE = "last_odds.json"
ENTRIES_FILE = "today_entries.json"

async def fetch_odds_safe():
    async with async_playwright() as p:
        # 增加啟動參數偽裝
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        current_odds = {}
        
        try:
            # 延長超時並模擬真人滾動
            await page.goto(URL, wait_until="load", timeout=90000)
            await page.mouse.wheel(0, 500) 
            await asyncio.sleep(5)
            
            # 獲取所有賠率數字
            odds_elements = await page.query_selector_all(".win_odds")
            for i, el in enumerate(odds_elements):
                text = (await el.inner_text()).strip()
                if text and text.replace('.', '').isdigit():
                    current_odds[str(i+1)] = float(text)
        except Exception as e:
            print(f"抓取異常: {e}")
        finally:
            await browser.close()
        return current_odds

async def main():
    current_odds = await fetch_odds_safe()
    if not current_odds:
        print("未能獲取當前賠率數據")
        return

    # 載入舊數據
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        with open(ODDS_FILE, 'r') as f: last_odds = json.load(f)

    # 載入馬名 (如果有的話)
    entries = {}
    if os.path.exists(ENTRIES_FILE):
        try:
            with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
                entries = json.load(f).get('entries', {})
        except: pass

    alerts = []
    for no, odds in current_odds.items():
        if no in last_odds:
            old = last_odds[no]
            # 觸發門檻：跌幅 15%
            if old > odds and (old - odds) / old >= 0.15:
                name = entries.get(no, {}).get('name', f'{no}號馬')
                alerts.append(f"🏇 *落飛警報*\n🎯 推薦：{name}\n📉 賠率：{old} ➡️ *{odds}*")

    if alerts and TOKEN and CHAT_ID:
        msg = "🔔 *【大戶資金即時監控】*\n\n" + "\n\n".join(alerts)
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    
    # 存檔
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
