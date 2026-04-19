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
            print(f"🚀 正在打開網頁: {URL}")
            # 1. 導航到網頁
            await page.goto(URL, wait_until="domcontentloaded", timeout=90000)
            
            # 2. 【強力等待】精準監控賠率元素出現
            print("⏳ 正在等待賠率表格渲染 (最多 30 秒)...")
            try:
                # 等待 .win_odds 這個 Class 出現在頁面上
                await page.wait_for_selector(".win_odds", timeout=30000)
                print("✅ 發現賠率數據！")
            except Exception as e:
                print(f"⚠️ 警告：超過 30 秒未見賠率標籤，嘗試強制讀取當前內容...")
            
            # 額外給予 5 秒緩衝時間，確保所有馬號賠率都載入完畢
            await asyncio.sleep(5) 

            # 3. 獲取當前場次
            try:
                race_tag = await page.locator(".raceNoTab.active").inner_text()
                race_no = "".join(filter(str.isdigit, race_tag))
                print(f"🏇 當前場次: 第 {race_no} 場")
            except: pass

            # 4. 抓取賠率單元格
            odds_elements = await page.query_selector_all(".win_odds")
            for i, el in enumerate(odds_elements):
                text = (await el.inner_text()).strip()
                # 過濾掉橫槓或空值，只保留數字
                if text and text.replace('.', '').isdigit():
                    current_odds[str(i+1)] = float(text)
                    
        except Exception as e:
            print(f"❌ 抓取過程發生異常: {e}")
        finally:
            await browser.close()
        return current_odds, race_no

async def main():
    current_odds, race_no = await fetch_odds_safe()
    
    # 【防空機制】如果最終沒抓到數據，則不更新基準檔案
    if not current_odds:
        print("❌ 本次抓取結果為空，保留上次的基準數據，防止數據清零。")
        return

    # 載入上次紀錄
    last_odds = {}
    if os.path.exists(ODDS_FILE):
        try:
            with open(ODDS_FILE, 'r') as f:
                last_odds = json.load(f)
        except: pass

    # 載入 14 匹馬佔位符
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
            # 核心邏輯：跌幅 >= 15% 觸發報警
            if old > odds and (old - odds) / old >= 0.15:
                name = entries.get(no, {}).get('name', f'{no}號馬')
                msg = (
                    f"🔔 *落飛警報：第 {race_no} 場*\n"
                    f"🎯 *精選心水*：{no}號 {name}\n"
                    f"📉 *賠率變動*：{old} ➡️ *{odds}*\n"
                    f"⚡ *提示*：發現大戶資金流入！"
                )
                alerts.append(msg)

    # 發送 Telegram
    if alerts:
        send_tg("📢 *【HKJC 即時大戶監控】*\n\n" + "\n\n".join(alerts))
        print(f"📢 已發送 {len(alerts)} 條落飛通知")
    else:
        print("📊 掃描完成：賠率波幅正常。")
    
    # 存檔本次數據作為下次比對的基準
    with open(ODDS_FILE, 'w') as f:
        json.dump(current_odds, f)
    print(f"✅ 基準線更新成功：共記錄 {len(current_odds)} 匹馬")

if __name__ == "__main__":
    asyncio.run(main())
