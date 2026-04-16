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
        try:
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_selector(".win_odds", timeout=20000)
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
        return current_odds

async def main():
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        try:
            with open(ODDS_FILE, 'r') as f: last_odds = json.load(f)
        except: pass

    current_odds = await fetch_current_odds()
    if not current_odds: return

    alerts = []
    for no, odds in current_odds.items():
        if no in last_odds:
            old_odds = last_odds[no]
            if old_odds > odds:
                drop_rate = (old_odds - odds) / old_odds
                # 門檻：跌幅 > 15% 且 賠率 < 30 (排除超冷門亂跳)
                if drop_rate >= 0.15 and odds < 30:
                    info = get_horse_info(no)
                    if info:
                        name = info.get('name', '未知')
                        jockey = info.get('jockey', '未知')
                        trainer = info.get('trainer', '未知')
                        draw = info.get('draw', '-')
                        
                        # --- 格式化單匹馬報告 ---
                        report = (
                            f"🏇 *落飛預警：{no}號 {name}*\n"
                            f"🎯 *狀態*：賠率由 {old_odds} 📉 *{odds}* ({drop_rate:.0%})\n"
                            f"📊 *優勢*：{draw}檔 | {jockey} ({trainer})\n"
                            f"⚡ *提示*：大戶資金流入，留意走勢"
                        )
                        alerts.append(report)

    if alerts:
        now = datetime.now().strftime("%H:%M:%S")
        final_msg = f"🔔 *【即時賽事監控】* ({now})\n" + "─" * 15 + "\n\n" + "\n\n".join(alerts)
        send_telegram_msg(final_msg)

    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
