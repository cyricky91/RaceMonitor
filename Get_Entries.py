import asyncio
import json
import logging
from playwright.async_api import async_playwright
from datetime import datetime

DATA_FILE = "today_entries.json"
logging.basicConfig(level=logging.INFO)

async def fetch_all_entries():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 使用更真實的手機環境模擬
        iphone = p.devices['iPhone 13']
        context = await browser.new_context(**iphone)
        page = await context.new_page()
        entries_data = {}
        
        try:
            logging.info("正在執行深度渲染掃描...")
            # 訪問排位表
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="networkidle")
            
            # 等待馬匹名稱的鏈接標籤出現
            await page.wait_for_selector("a[href*='HorseId=']", timeout=30000)
            
            # 獲取所有馬匹名稱鏈接
            horse_links = await page.locator("a[href*='HorseId=']").all()
            
            for i, link in enumerate(horse_links):
                name_text = await link.inner_text()
                if name_text and not name_text.isdigit():
                    # 清理名稱（移除括號等）
                    clean_name = name_text.strip().split('(')[0].strip()
                    # 使用 1, 2, 3... 作為 Key
                    entries_data[str(i+1)] = {
                        "name": clean_name,
                        "jockey": "-", "trainer": "-", "draw": "-"
                    }
            
            logging.info(f"✅ 深度掃描成功！共發現 {len(entries_data)} 匹馬。")
        except Exception as e:
            logging.error(f"深度掃描失敗: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    data = asyncio.run(fetch_all_entries())
    output = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "horse_count": len(data),
        "entries": data
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
