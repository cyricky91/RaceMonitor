import os
import asyncio
from playwright.async_api import async_playwright
import requests

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

async def get_odds():
    async with async_playwright() as p:
        # 啟動瀏覽器
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 前往馬會賠率頁面
            await page.goto("https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=ch", timeout=60000)
            # 等待賠率表格加載 (這裡使用一個馬會頁面常見的選擇器)
            await page.wait_for_selector(".win_odds", timeout=15000)
            
            # 測試：抓取第一匹馬的賠率
            odds = await page.locator(".win_odds").first.inner_text()
            return f"✅ 成功抓取數據！目前第一匹馬賠率為: {odds}"
        except Exception as e:
            return f"❌ 抓取失敗: {str(e)}"
        finally:
            await browser.close()

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={text}"
    requests.get(url)

if __name__ == "__main__":
    result = asyncio.run(get_odds())
    send_msg(result)
