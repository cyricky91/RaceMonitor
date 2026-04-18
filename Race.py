import os
import asyncio
import json
import logging
from playwright.async_api import async_playwright
import requests
from datetime import datetime

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
# 改用手機版賠率連結
URL = "https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=ch"
ODDS_FILE = "last_odds.json"
ENTRIES_FILE = "today_entries.json"

logging.basicConfig(level=logging.INFO)

def send_telegram_msg(message):
    if not TOKEN or not CHAT_ID: return
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                  data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})

async def fetch_current_odds():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        iphone = p.devices['iPhone 13']
        context = await browser.new_context(**iphone)
        page = await context.new_page()
        current_odds = {}
        try:
            await page.goto(URL, wait_until="networkidle")
            await page.wait_for_timeout(5000)
            
            # 手機版賠率通常在 .winOddsCell 裡
            elements = await page.locator(".win_odds").all()
            for i, el in enumerate(elements):
                val = (await el.inner_text()).strip()
                if val.replace('.','').isdigit():
                    current_odds[str(i+1)] = float(val)
        except Exception as e:
            logging.error(f"賠率異常: {e}")
        finally:
            await browser.close()
        return current_odds

async def main():
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        try:
            with open(ODDS_FILE, 'r') as f: last_odds = json.load(f)
        except: pass

    current_odds = await fetch_current_odds()
    if not current_odds: return

    entries = {}
    if os.path.exists(ENTRIES_FILE):
        with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
            entries = json.load(f).get('entries', {})

    alerts = []
    for no, odds in current_odds.items():
        if no in last_odds:
            old_odds = last_odds[no]
            # 跌幅 15% 觸發
            if old_odds > odds and (old_odds - odds) / old_odds >= 0.15:
                name = entries.get(no, {}).get('name', f'馬匹{no}')
                alerts.append(f"🏇 *落飛警報*\n🎯 {no}號 {name}\n📉 賠率：{old_odds} ➡️ *{odds}*")

    if alerts:
        send_telegram_msg("🔔 *【即時資金流監控】*\n\n" + "\n\n".join(alerts))
    
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
