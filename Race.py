import os
import asyncio
import json
import requests
from playwright.async_api import async_playwright

# 從 GitHub Secrets 獲取設定
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
URL = "https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=ch"
ODDS_FILE = "last_odds.json"
ENTRIES_FILE = "today_entries.json"

def send_tg(msg):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"Telegram 發送失敗: {e}")

async def fetch_odds_safe():
    async with async_playwright() as p:
        # 增加偽裝參數，減少被馬會封鎖機率
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        current_odds = {}
        race_no = "1"
        
        try:
            # 延長加載時間，給予 10 秒緩衝確保 JS 渲染完成
            await page.goto(URL, wait_until="networkidle", timeout=90000)
            await asyncio.sleep(10) 
            
            # 獲取當前場次標籤
            try:
                race_tag = await page.locator(".raceNoTab.active").inner_text()
                race_no = "".join(filter(str.isdigit, race_tag))
            except: pass

            # 抓取所有賠率單元格 (.win_odds)
            odds_elements = await page.query_selector_all(".win_odds")
            for i, el in enumerate(odds_elements):
                text = (await el.inner_text()).strip()
                if text and text.replace('.', '').isdigit():
                    current_odds[str(i+1)] = float(text)
        except Exception as e:
            print(f"抓取異常: {e}")
        finally:
            await browser.close()
        return current_odds, race_no

async def main():
    current_odds, race_no = await fetch_odds_safe()
    
    # 【防空機制】如果沒抓到數據，不更新檔案，直接退出
    if not current_odds:
        print("❌ 本次抓取失敗或頁面未加載數據，保留上次的基準數據。")
        return

    # 載入上一次的賠率紀錄進行比對
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        try:
            with open(ODDS_FILE, 'r') as f:
                last_odds = json.load(f)
        except: pass

    # 載入馬名佔位符
    entries = {}
    if os.path.exists(ENTRIES_FILE):
        try:
            with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
                entries = json.load(f).get('entries', {})
        except: pass

    alerts = []
    for no, odds in current_odds.items():
        if no in last_odds:
            old = last_odds[no]
            # 比對邏輯：跌幅超過 15% 觸發
            if old > odds and (old - odds) / old >= 0.15:
                name = entries.get(no, {}).get('name', f'{no}號馬')
                msg = (
                    f"🏇 *落飛警報：第 {race_no} 場*\n"
                    f"🎯 *精選心水*：{no}號 {name}\n"
                    f"📉 *賠率變動*：{old} ➡️ *{odds}*\n"
                    f"⚡ *狀態*：發現大戶資金流入！"
                )
                alerts.append(msg)

    # 如果有警報，發送 Telegram
    if alerts:
        send_tg("🔔 *【HKJC 即時大戶監控】*\n\n" + "\n\n".join(alerts))
    else:
        print("📊 賠率變動未達門檻。")
    
    # 【存檔】只有在有成功抓到數據時才寫入，成為下次比對的基準
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)
    print(f"✅ 成功更新 {len(current_odds)} 匹馬的賠率基準")

if __name__ == "__main__":
    asyncio.run(main())
