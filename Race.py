import os
import asyncio
import json
import logging
from playwright.async_api import async_playwright
import requests
from datetime import datetime

# --- 配置 ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
URL = "https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=ch"
ODDS_FILE = "last_odds.json"
ENTRIES_FILE = "today_entries.json"

logging.basicConfig(level=logging.INFO)

def send_telegram_msg(message):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=payload, timeout=10)

def get_horse_info(horse_no):
    if os.path.exists(ENTRIES_FILE):
        with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f).get('entries', {})
            return data.get(str(horse_no))
    return None

async def fetch_current_odds():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        current_odds = {}
        try:
            logging.info("正在抓取賠率...")
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            
            # 檢查是否有賠率表格，若無則不報錯，優雅退出
            odds_table = page.locator(".win_odds")
            if await odds_table.count() == 0:
                logging.warning("目前頁面無有效賠率數據。")
                return {}

            rows = await page.locator("tr.update_odds_row").all()
            for row in rows:
                try:
                    no = (await row.locator(".horse_no").inner_text()).strip()
                    odds_val = (await row.locator(".win_odds").inner_text()).strip()
                    if odds_val.replace('.', '').isdigit():
                        current_odds[no] = float(odds_val)
                except: continue
        finally:
            await browser.close()
        return current_odds

async def main():
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        with open(ODDS_FILE, 'r') as f: last_odds = json.load(f)

    current_odds = await fetch_current_odds()
    if not current_odds: return

    alerts = []
    for no, odds in current_odds.items():
        if no in last_odds:
            old_odds = last_odds[no]
            # 跌幅 > 20% 觸發
            if old_odds > odds and (old_odds - odds) / old_odds >= 0.20:
                info = get_horse_info(no)
                name = info.get('name', '未知') if info else "新馬/未知"
                draw = info.get('draw', '-') if info else "-"
                jockey = info.get('jockey', '未知') if info else "未知"
                trainer = info.get('trainer', '未知') if info else "未知"

                # 🐴 依照你要求的格式優化
                report = (
                    f"🏇 *落飛預警：第 X 場 {no}號 {name}*\n"
                    f"🎯 *心水狀態*：{old_odds} 📉 *{odds}*\n"
                    f"📊 *優勢*：{draw}檔 | {jockey} ({trainer})\n"
                    f"⚡ *提示*：大戶進場，賠率急降！"
                )
                alerts.append(report)

    if alerts:
        header = f"🔔 *【即時監控報告】* {datetime.now().strftime('%H:%M:%S')}\n"
        send_telegram_msg(header + "\n" + "\n\n".join(alerts))

    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
