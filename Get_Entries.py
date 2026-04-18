import asyncio
import json
import logging
from playwright.async_api import async_playwright
from datetime import datetime

DATA_FILE = "today_entries.json"
logging.basicConfig(level=logging.INFO)

async def fetch_entries():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 使用極其真實的瀏覽器指紋
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={"Referer": "https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx"}
        )
        page = await context.new_page()
        entries_data = {}
        
        try:
            logging.info("切換至原始賽程表路徑...")
            # 這是馬會最基礎的賽卡頁面
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx", wait_until="load", timeout=60000)
            await page.wait_for_timeout(3000)
            
            # 使用更原始的選擇器抓取馬名
            # 馬會賽卡中，馬名通常在含有 'HorseId=' 的鏈接文字中
            links = await page.locator("a[href*='HorseId=']").all()
            for link in links:
                text = await link.inner_text()
                if text and not text.isdigit():
                    # 嘗試獲取它旁邊的馬號
                    try:
                        # 向上找父元素再找馬號，或直接利用順序
                        name = text.strip().split('(')[0]
                        # 這裡暫時用索引或馬名作為 Key，確保資料庫有東西
                        entries_data[str(len(entries_data)+1)] = {
                            "name": name,
                            "jockey": "-", "trainer": "-", "draw": "-"
                        }
                    except: pass
            
            logging.info(f"最終解析成功：找到 {len(entries_data)} 匹馬")
        except Exception as e:
            logging.error(f"抓取失敗: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    data = asyncio.run(fetch_entries())
    output = {"update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "entries": data}
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
