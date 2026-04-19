import os
import asyncio
import json
import requests
from playwright.async_api import async_playwright

# 從 GitHub Secrets 獲取設定
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
# 切換到排位表頁面，這裡的數據相對容易被 GitHub Actions 抓取
URL = "https://racing.hkjc.com/racing/Info/meeting/Startlist/chinese/local/"
ODDS_FILE = "last_odds.json"
ENTRIES_FILE = "today_entries.json"

def send_tg(msg):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"Telegram 發送失敗: {e}")

async def fetch_odds_final_boss():
    async with async_playwright() as p:
        # 使用 Chromium 並增加基本偽裝
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        current_odds = {}
        race_no = "1"
        
        try:
            print(f"🚀 正在切換路徑，訪問排位表: {URL}")
            # 導航至排位表
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(8) # 等待數據填充

            # 嘗試抓取當前場次 (從頁面標題或標籤)
            try:
                race_no_text = await page.locator(".font_white.f_left.f_fs14").first.inner_text()
                race_no = "".join(filter(str.isdigit, race_no_text)) or "1"
            except: pass

            # 抓取所有賠率單元格 
            # 排位表中獨贏賠率通常帶有特殊的 class (例如 tdWinOdds 或 f_fs12 f_fr)
            print("🔎 正在提取表格賠率數據...")
            odds_elements = await page.query_selector_all("td.f_fs12.f_fr")
            
            temp_odds = []
            for el in odds_elements:
                txt = (await el.inner_text()).strip()
                # 排除掉獨贏以外的賠率 (通常獨贏賠率在前面)
                if txt.replace('.', '').isdigit() and 1.0 < float(txt) < 1000:
                    temp_odds.append(float(txt))

            # 對應馬號 (1-14)
            for i, val in enumerate(temp_odds):
                if i < 14:
                    current_odds[str(i+1)] = val
            
            if current_odds:
                print(f"✅ 成功! 抓到第 {race_no} 場共 {len(current_odds)} 匹馬的賠率")

        except Exception as e:
            print(f"❌ 抓取異常: {e}")
        finally:
            await browser.close()
        return current_odds, race_no

async def main():
    current_odds, race_no = await fetch_odds_final_boss()
    
    if not current_odds:
        print("❌ 依然抓不到數據。這代表 GitHub IP 被馬會全面封鎖。")
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
                    f"⚡ *提示*：發現大戶資金流入！"
                )
                alerts.append(msg)

    if alerts:
        send_tg("📢 *【HKJC 即時大戶監控】*\n\n" + "\n\n".join(alerts))
    
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)
    print(f"✅ 基準線已更新。")

if __name__ == "__main__":
    asyncio.run(main())
