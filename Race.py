import os
import asyncio
import json
import logging
from playwright.async_api import async_playwright
import requests
from datetime import datetime

# --- 配置區 ---
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
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        logging.error(f"Telegram 發送失敗: {e}")

def get_horse_info(horse_no):
    if os.path.exists(ENTRIES_FILE):
        try:
            with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
                content = json.load(f)
                entries = content.get('entries', {})
                return entries.get(str(horse_no))
        except: pass
    return None

async def fetch_current_odds():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
        page = await context.new_page()
        current_odds = {}
        race_no = "X"
        try:
            logging.info("正在訪問馬會賠率頁面...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # 偵測目前是第幾場
            try:
                race_no_raw = await page.locator(".raceNo").first.inner_text()
                race_no = "".join(filter(str.isdigit, race_no_raw))
            except: pass

            # 檢查賠率表是否加載
            if await page.locator(".win_odds").count() == 0:
                logging.info("目前無賠率數據顯示。")
                return {}, race_no

            rows = await page.locator("tr.update_odds_row").all()
            for row in rows:
                try:
                    no = (await row.locator(".horse_no").inner_text()).strip()
                    odds_text = (await row.locator(".win_odds").inner_text()).strip()
                    if odds_text.replace('.', '').isdigit():
                        current_odds[no] = float(odds_text)
                except: continue
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
    if not current_odds: return

    alerts = []
    for no, odds in current_odds.items():
        if no in last_odds:
            old_odds = last_odds[no]
            if old_odds > odds:
                drop_rate = (old_odds - odds) / old_odds
                # 門檻：跌幅 > 15% 且賠率具備監控價值
                if drop_rate >= 0.15 and 2.0 < odds < 50.0:
                    info = get_horse_info(no)
                    name = info.get('name', '未知馬名') if info else "即時新馬"
                    draw = info.get('draw', '-') if info else "-"
                    jockey = info.get('jockey', '未知') if info else "未知"
                    trainer = info.get('trainer', '未知') if info else "未知"
                    
                    # --- 依照你要求的格式進行 Emoji 分類 ---
                    report = (
                        f"🏇 *落飛警報：第 {race_no} 場 {no}號 {name}*\n"
                        f"🎯 *心水狀態*：{old_odds} 📉 *{odds}* (跌幅 {drop_rate:.0%})\n"
                        f"📊 *優勢*：{draw}檔 | {jockey} ({trainer})\n"
                        f"⚡ *提示*：資金異動，建議留意走勢"
                    )
                    alerts.append(report)

    if alerts:
        now = datetime.now().strftime("%H:%M:%S")
        send_telegram_msg(f"🔔 *【HKJC 資金流向監控】* ({now})\n" + "─" * 15 + "\n\n" + "\n\n".join(alerts))
    elif not last_odds:
        logging.info("首輪運行，已記錄基準賠率。")

    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
