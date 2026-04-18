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
        race_no = "X"
        try:
            logging.info("正在訪問馬會賠率頁面...")
            # 增加重試與等待邏輯
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # 嘗試偵測場次
            try:
                race_no_tag = page.locator(".raceNo").first
                if await race_no_tag.count() > 0:
                    race_no = "".join(filter(str.isdigit, await race_no_tag.inner_text()))
            except: pass

            # 檢查是否有賠率標籤
            win_odds_locator = page.locator(".win_odds")
            if await win_odds_locator.count() == 0:
                logging.warning("找不到預期的賠率標籤，可能尚未開售。")
                return {}, race_no

            # 精確抓取數據行
            rows = await page.locator("tr.update_odds_row").all()
            for row in rows:
                no = (await row.locator(".horse_no").inner_text()).strip()
                odds_text = (await row.locator(".win_odds").inner_text()).strip()
                if odds_text.replace('.', '').isdigit():
                    current_odds[no] = float(odds_text)
                    
        except Exception as e:
            logging.error(f"賠率抓取失敗: {e}")
        finally:
            await browser.close()
        return current_odds, race_no

async def main():
    # 讀取舊數據
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        with open(ODDS_FILE, 'r') as f: last_odds = json.load(f)

    current_odds, race_no = await fetch_current_odds()
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
            # 設定 15% 跌幅預警
            if old_odds > odds and (old_odds - odds) / old_odds >= 0.15:
                info = entries.get(no, {})
                name = info.get('name', '未知')
                jockey = info.get('jockey', '未知')
                draw = info.get('draw', '-')
                
                # 🏇 使用你要求的格式
                msg = (
                    f"🏇 *落飛警報：第 {race_no} 場*\n"
                    f"🎯 *心水推薦*：{no}號 {name}\n"
                    f"📊 *優勢分析*：{draw}檔 | {jockey}\n"
                    f"⚡ *賠率變動*：{old_odds} 📉 *{odds}*"
                )
                alerts.append(msg)

    if alerts:
        send_telegram_msg(f"🔔 *【HKJC 即時大戶監控】*\n\n" + "\n\n".join(alerts))
    
    # 儲存新數據
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
