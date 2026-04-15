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
DATA_FILE = "last_odds.json"

logging.basicConfig(level=logging.INFO)

def send_telegram_msg(message):
    if not TOKEN or not CHAT_ID:
        logging.error("缺少 Telegram Token 或 CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        logging.info(f"Telegram 發送失敗: {e}")

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
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        current_race_odds = {}
        try:
            logging.info(f"正在前往馬會網頁...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # 【關鍵修正】嘗試多個可能的選擇器，確保賽後也能抓到
            selectors = [".win_odds", ".oddsTable", "tr.update_odds_row"]
            found = False
            for s in selectors:
                try:
                    await page.wait_for_selector(s, timeout=10000)
                    found = True
                    break
                except:
                    continue
            
            if not found:
                logging.warning("找不到預期的賠率標籤")
                return {}

            # 抓取表格中所有行
            # 兼容：進行中的 .update_odds_row 和 完結後的普通 tr
            rows = await page.locator("tr").all()
            for row in rows:
                try:
                    # 嘗試抓取馬號和賠率（通常在特定 class 內）
                    no_element = await row.locator(".horse_no").first
                    odds_element = await row.locator(".win_odds").first
                    
                    no_text = await no_element.inner_text()
                    odds_text = await odds_element.inner_text()
                    
                    no = no_text.strip()
                    odds_val = odds_text.strip()

                    # 排除非數字內容 (如 SCR, -, 或 標題)
                    if no.isdigit() and odds_val.replace('.','').isdigit():
                        current_race_odds[no] = float(odds_val)
                except:
                    continue
            
            logging.info(f"成功抓取 {len(current_race_odds)} 匹馬數據")
        except Exception as e:
            logging.error(f"抓取過程出錯: {e}")
        finally:
            await browser.close()
        return current_race_odds

async def main():
    last_odds = load_previous_odds()
    current_odds = await fetch_odds()
    
    if not current_odds:
        # 如果今日賽事已完結，通常表格會消失或清空
        send_telegram_msg("🏇 *賽馬監控報號*\n今日賽事可能已完結，或目前暫無即時賠率數據。")
        return

    alerts = []
    for no, odds in current_odds.items():
        if no in last_odds:
            old_odds = last_odds[no]
            if old_odds > odds:
                drop_rate = (old_odds - odds) / old_odds
                if drop_rate >= 0.2: 
                    alerts.append(f"🐴 {no}號: {old_odds} ➡️ *{odds}* (跌 {drop_rate:.1%})")

    if alerts:
        now = datetime.now().strftime("%H:%M:%S")
        msg = f"⚠️ *【落飛警報】* ({now})\n\n" + "\n".join(alerts)
        send_telegram_msg(msg)
    else:
        # 為了測試方便，第一次抓到數據時發個成功通知
        if not last_odds:
            send_telegram_msg(f"✅ *機器人監控中*\n已成功取得 {len(current_odds)} 匹馬的初始賠率，正在等待變動...")

    save_current_odds(current_odds)

if __name__ == "__main__":
    asyncio.run(main())
