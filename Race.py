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
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        current_odds = {}
        race_no = "1"
        try:
            logging.info("正在訪問賠率頁面...")
            # 這裡增加了一個特殊的等待條件
            await page.goto(URL, wait_until="load")
            await page.wait_for_selector(".win_odds", timeout=15000)
            
            # 偵測場次
            try:
                race_no = await page.locator("#raceNoTab td.active").inner_text()
                race_no = "".join(filter(str.isdigit, race_no))
            except: pass

            # 使用暴力法遍歷所有可能包含賠率的行
            rows = await page.locator("tr").all()
            for row in rows:
                if await row.locator("td.horse_no").count() > 0:
                    no = (await row.locator("td.horse_no").inner_text()).strip()
                    odds_cell = row.locator("td.win_odds")
                    if await odds_cell.count() > 0:
                        odds_text = (await odds_cell.inner_text()).strip()
                        if odds_text.replace('.', '').isdigit():
                            current_odds[no] = float(odds_text)
        except Exception as e:
            logging.error(f"賠率抓取失敗: {e}")
        finally:
            await browser.close()
        return current_odds, race_no

async def main():
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        try:
            with open(ODDS_FILE, 'r') as f: last_odds = json.load(f)
        except: pass

    current_odds, race_no = await fetch_current_odds()
    if not current_odds: 
        logging.warning("未能獲取當前賠率數據。")
        return

    # 讀取排位資料庫
    entries = {}
    if os.path.exists(ENTRIES_FILE):
        try:
            with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
                entries = json.load(f).get('entries', {})
        except: pass

    alerts = []
    for no, odds in current_odds.items():
        if no in last_odds:
            old_odds = last_odds[no]
            if old_odds > odds and (old_odds - odds) / old_odds >= 0.15:
                info = entries.get(no, {})
                report = (
                    f"🏇 *落飛警報：第 {race_no} 場 {no}號 {info.get('name', '未知')}*\n"
                    f"🎯 *賠率變動*：{old_odds} ➡️ *{odds}*\n"
                    f"📊 *優勢*：{info.get('draw','-')}檔 | {info.get('jockey','-')}\n"
                    f"⚡ *提示*：發現異常大注資金流入！"
                )
                alerts.append(report)

    if alerts:
        send_telegram_msg(f"🔔 *【HKJC 資金監控報告】*\n" + "─"*15 + "\n\n" + "\n\n".join(alerts))
    
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
