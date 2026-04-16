import os
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
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 1024},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()
        entries_data = {}
        
        try:
            logging.info("正在前往排位表頁面...")
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5) # 確保 JS 渲染
            
            # 暴力掃描所有 td 標籤
            rows = await page.locator("tr").all()
            for row in rows:
                cells = await row.locator("td").all()
                if len(cells) >= 6:
                    # 嘗試從第一欄提取所有數字
                    raw_no = await cells[0].inner_text()
                    no = "".join(filter(str.isdigit, raw_no.strip()))
                    
                    if no and 1 <= int(no) <= 14:
                        entries_data[no] = {
                            "name": (await cells[2].inner_text()).strip().split('(')[0],
                            "jockey": (await cells[3].inner_text()).strip(),
                            "trainer": (await cells[4].inner_text()).strip(),
                            "draw": (await cells[5].inner_text()).strip(),
                            "update_at": datetime.now().strftime("%H:%M:%S")
                        }
        except Exception as e:
            logging.error(f"抓取出錯: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    data = asyncio.run(fetch_entries())
    
    # 【關鍵：加入時間戳】確保每次產出的 JSON 內容都不同，強制 Git 必須提交
    import time
    final_output = {
        "update_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "horse_count": len(data),
        "entries": data
    }

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=4)
    logging.info(f"--- 檔案已成功寫入 {DATA_FILE} ---")
