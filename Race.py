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
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

async def fetch_odds_safe():
    async with async_playwright() as p:
        # 增加偽裝參數，減少被馬會封鎖機率
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        current_odds = {}
        race_no = "1"
        
        try:
            await page.goto(URL, wait_until="load", timeout=90000)
            await asyncio.sleep(5) # 給予渲染時間
            
            # 嘗試抓取當前場次
            try:
                race_tag = await page.locator(".raceNoTab.active").inner_text()
                race_no = "".join(filter(str.isdigit, race_tag))
            except: pass

            # 抓取賠率
            odds_elements = await page.query_selector_all(".win_odds")
            for i, el in enumerate(odds_elements):
                text = (await el.inner_text()).strip()
                if text and text.replace('.', '').isdigit():
                    current_odds[str(i+1)] = float(text)
        except Exception as e:
            print(f"抓取異常: {e}")
        finally:
            await browser.close()
        return current_odds, race_no

async def main():
    current_odds, race_no = await fetch_odds_safe()
    if not current_odds: return

    last_odds = {}
    if os.path.exists(ODDS_FILE):
        with open(ODDS_FILE, 'r') as f: last_odds = json.load(f)

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
            # 實戰門檻：跌幅 15%
            if old > odds and (old - odds) / old >= 0.15:
                name = entries.get(no, {}).get('name', f'{no}號馬')
                msg = (
                    f"🏇 *落飛警報：第 {race_no} 場*\n"
                    f"🎯 *精選心水*：{no}號 {name}\n"
                    f"📉 *變動*：{old} ➡️ *{odds}*\n"
                    f"⚡ *狀態*：發現大戶資金流入！"
                )
                alerts.append(msg)

    if alerts:
        send_tg("🔔 *【HKJC 即時大戶監控】*\n\n" + "\n\n".join(alerts))
    
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
