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
        # 使用最高等級的偽裝參數
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        current_odds = {}
        race_no = "1"
        
        try:
            print(f"🚀 正在開啟網頁: {URL}")
            # 等待網路完全空閒
            await page.goto(URL, wait_until="networkidle", timeout=90000)
            
            # 給予超長緩衝時間 (15秒)，應對 GitHub Actions 的網路延遲
            print("⏳ 深度等待數據渲染 (15s)...")
            await asyncio.sleep(15) 

            # 獲取場次
            try:
                race_tag = await page.locator(".raceNoTab.active").inner_text()
                race_no = "".join(filter(str.isdigit, race_tag))
            except: pass

            # --- 方案 A: 標準標籤抓取 ---
            print("🔎 嘗試方案 A (CSS Selector)...")
            odds_elements = await page.query_selector_all(".win_odds")
            temp_odds = []
            for el in odds_elements:
                text = (await el.inner_text()).strip()
                if text and text.replace('.', '').isdigit():
                    temp_odds.append(float(text))
            
            # --- 方案 B: 暴力掃描所有表格單元格 (如果 A 失敗) ---
            if not temp_odds:
                print("🔎 方案 A 失敗，執行方案 B (Table Cell Scan)...")
                td_elements = await page.query_selector_all("td")
                for td in td_elements:
                    # 檢查 class 是否包含 win_odds
                    cls = await td.get_attribute("class") or ""
                    txt = (await td.inner_text()).strip()
                    if "win_odds" in cls and txt.replace('.', '').isdigit():
                        temp_odds.append(float(txt))

            # 將結果填入字典 (1-14號)
            for i, val in enumerate(temp_odds):
                if i < 14: # 香港通常最多 14 匹馬
                    current_odds[str(i+1)] = val

            if current_odds:
                print(f"✅ 成功抓取到 {len(current_odds)} 匹馬的賠率")
            
        except Exception as e:
            print(f"❌ 抓取過程異常: {e}")
        finally:
            await browser.close()
        return current_odds, race_no

async def main():
    current_odds, race_no = await fetch_odds_safe()
    
    # 【防空機制】
    if not current_odds:
        print("❌ 最終抓取無數據，保留上次紀錄，停止本次對比。")
        return

    # 載入上次數據
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
            # 跌幅 15% 門檻
            if old > odds and (old - odds) / old >= 0.15:
                name = entries.get(no, {}).get('name', f'{no}號馬')
                msg = (
                    f"🔔 *落飛警報：第 {race_no} 場*\n"
                    f"🎯 *精選心水*：{no}號 {name}\n"
                    f"📉 *賠率變動*：{old} ➡️ *{odds}*\n"
                    f"⚡ *提示*：監測到資金異常湧入！"
                )
                alerts.append(msg)

    # 發送通知
    if alerts:
        send_tg("📢 *【HKJC 即時大戶監控】*\n\n" + "\n\n".join(alerts))
    else:
        print("📊 數據比對完成，波幅正常。")
    
    # 存檔本次數據
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)
    print(f"✅ 基準線已更新，場次: {race_no}")

if __name__ == "__main__":
    asyncio.run(main())
