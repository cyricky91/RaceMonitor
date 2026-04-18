import os
import asyncio
import json
import logging
from playwright.async_api import async_playwright
import requests
from datetime import datetime

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
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
        context = await browser.new_context(user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15")
        page = await context.new_page()
        current_odds = {}
        try:
            await page.goto(URL, wait_until="load")
            await page.wait_for_timeout(5000)
            # 暴力抓取頁面上所有看似賠率的數字
            odds_elements = await page.locator(".win_odds").all()
            for i, el in enumerate(odds_elements):
                val = (await el.inner_text()).strip()
                if val.replace('.','').isdigit():
                    current_odds[str(i+1)] = float(val)
        finally:
            await browser.close()
        return current_odds

async def main():
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        with open(ODDS_FILE, 'r') as f: last_odds = json.load(f)

    current_odds = await fetch_current_odds()
    if not current_odds: return

    # 讀取排位數據
    entries = {}
    if os.path.exists(ENTRIES_FILE):
        with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
            entries = json.load(f).get('entries', {})

    alerts = []
    for no, odds in current_odds.items():
        if no in last_odds:
            old_odds = last_odds[no]
            if old_odds > odds and (old_odds - odds) / old_odds >= 0.15:
                name = entries.get(no, {}).get('name', f'馬匹 {no}')
                alerts.append(f"🏇 *落飛：{name}*\n📉 {old_odds} ➡️ *{odds}*")

    if alerts:
        send_telegram_msg(f"🔔 *【即時監控】*\n" + "\n".join(alerts))
    
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
