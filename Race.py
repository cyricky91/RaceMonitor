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
    if not TOKEN or not CHAT_ID:
        logging.error("缺少 Token 或 CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        logging.error(f"Telegram 發送失敗: {e}")

def get_horse_info(horse_no):
    """從 today_entries.json 獲取馬匹詳細資訊"""
    if os.path.exists(ENTRIES_FILE):
        try:
            with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
                content = json.load(f)
                # 兼容你目前的 JSON 結構 (含有 entries 或 data 鍵值)
                entries = content.get('entries') or content.get('data') or {}
                return entries.get(str(horse_no))
        except Exception as e:
            logging.error(f"讀取排位表出錯: {e}")
    return None

async def fetch_current_odds():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        page = await context.new_page()
        current_odds = {}
        try:
            logging.info("正在抓取即時賠率...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_selector(".win_odds", timeout=20000)
            
            rows = await page.locator("tr.update_odds_row").all()
            for row in rows:
                try:
                    no_text = await row.locator(".horse_no").inner_text()
                    odds_text = await row.locator(".win_odds").inner_text()
                    no = no_text.strip()
                    if odds_text.strip().replace('.', '').isdigit():
                        current_odds[no] = float(odds_text.strip())
                except:
                    continue
        except Exception as e:
            logging.error(f"賠率抓取失敗: {e}")
        finally:
            await browser.close()
        return current_odds

async def main():
    # 讀取舊賠率
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        with open(ODDS_FILE, 'r') as f:
            last_odds = json.load(f)

    current_odds = await fetch_current_odds()
    if not current_odds:
        logging.info("目前無賽事賠率。")
        return

    alerts = []
    for no, odds in current_odds.items():
        if no in last_odds:
            old_odds = last_odds[no]
            if old_odds > odds:
                drop_rate = (old_odds - odds) / old_odds
                # 設定跌幅超過 15% 觸發警報 (可自行調整)
                if drop_rate >= 0.15:
                    info = get_horse_info(no)
                    if info:
                        name = info.get('name', '未知')
                        jockey = info.get('jockey', '未知')
                        draw = info.get('draw', '-')
                        alerts.append(f"🐴 *{no}號 {name}* ({draw}檔)\n   騎練：{jockey}\n   賠率：{old_odds} ➡️ *{odds}* (跌{drop_rate:.0%})")
                    else:
                        alerts.append(f"🐴 *{no}號馬*\n   賠率：{old_odds} ➡️ *{odds}* (跌{drop_rate:.0%})")

    if alerts:
        now = datetime.now().strftime("%H:%M:%S")
        msg = f"⚠️ *【落飛預警】* ({now})\n\n" + "\n\n".join(alerts)
        send_telegram_msg(msg)
    elif not last_odds:
        send_telegram_msg(f"✅ *監控已啟動*\n已成功連結排位表，目前監控中。")

    # 儲存本次賠率供下次對比
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)

if __name__ == "__main__":
    asyncio.run(main())
