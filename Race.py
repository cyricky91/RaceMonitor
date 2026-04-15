import os
import asyncio
import json
import logging
from playwright.async_api import async_playwright
import requests

# --- 配置區 ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
URL = "https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=ch"
DATA_FILE = "last_odds.json"

logging.basicConfig(level=logging.INFO)

def send_telegram_msg(message):
    if not TOKEN or not CHAT_ID:
        logging.error("缺少 Telegram Token 或 Chat ID")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        logging.error(f"Telegram 發送失敗: {e}")

def load_previous_odds():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_current_odds(odds):
    with open(DATA_FILE, 'w') as f:
        json.dump(odds, f)

async def fetch_odds():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        current_race_odds = {}
        try:
            logging.info(f"正在前往: {URL}")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # 等待賠率表格出現
            await page.wait_for_selector(".win_odds", timeout=20000)
            
            # 抓取馬匹編號與賠率
            # 註：馬會網頁結構複雜，這裡使用常見的選擇器組合，若失效需根據當日網頁微調
            rows = await page.locator("tr.update_odds_row").all()
            for row in rows:
                try:
                    no = await row.locator(".horse_no").inner_text()
                    odds_text = await row.locator(".win_odds").inner_text()
                    current_race_odds[no.strip()] = float(odds_text.strip())
                except:
                    continue
                    
            logging.info(f"抓取成功，共有 {len(current_race_odds)} 匹馬數據")
        except Exception as e:
            logging.error(f"Playwright 抓取出錯: {e}")
        finally:
            await browser.close()
        return current_race_odds

async def main():
    last_odds = load_previous_odds()
    current_odds = await fetch_odds()
    
    if not current_odds:
        # 如果抓不到數據，發送一個測試訊息確認 Bot 正常
        send_telegram_msg("🏇 *賽馬監控報號*\n今日目前無賽事數據或網頁解析失敗。")
        return

    alerts = []
    for no, odds in current_odds.items():
        if no in last_odds:
            old_odds = last_odds[no]
            if old_odds > 0:
                drop_rate = (old_odds - odds) / old_odds
                if drop_rate >= 0.2:  # 跌幅 20%
                    alerts.append(f"馬匹 {no}號: {old_odds} ↘️ {odds} (跌 {drop_rate:.1%})")

    if alerts:
        msg = "⚠️ *【落飛警報】*\n" + "\n".join(alerts)
        send_telegram_msg(msg)
    else:
        logging.info("無顯著落飛情況")

    save_current_odds(current_odds)

if __name__ == "__main__":
    asyncio.run(main())
