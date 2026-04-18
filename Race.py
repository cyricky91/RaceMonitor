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
        page = await browser.new_page()
        current_odds = {}
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5) # 給予足夠渲染時間
            
            # 嘗試抓取所有賠率單元格
            cells = await page.locator(".win_odds").all()
            for i, cell in enumerate(cells):
                val = (await cell.inner_text()).strip()
                if val.replace('.','').isdigit():
                    current_odds[str(i+1)] = float(val)
        except Exception as e:
            logging.error(f"賠率抓取異常: {e}")
        finally:
            await browser.close()
        return current_odds

async def main():
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        with open(ODDS_FILE, 'r') as f: last_odds = json.load(f)

    current_odds = await fetch_current_odds()
    if not current_odds: 
        logging.info("暫無即時賠率數據。")
        return

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
                info = entries.get(no, {"name": f"馬匹{no}"})
                msg = (
                    f"🏇 *落飛警報*\n"
                    f"🎯 *目標*：{no}號 {info['name']}\n"
                    f"📊 *變動*：{old_odds} 📉 *{odds}*\n"
                    f"⚡ *提示*：資金異動中！"
                )
                alerts.append(msg)

    if alerts:
        send_telegram_msg("🔔 *【即時資金監控報告】*\n\n" + "\n\n".join(alerts))
    
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
