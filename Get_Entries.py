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
            # 增加 timeout 並等待網路閒置
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="networkidle", timeout=60000)
            
            # 確保內容已加載
            await asyncio.sleep(5)
            
            # 嘗試抓取排位表所有的行 (通常在 .ltable 下)
            # 我們改用更強大的選擇器，尋找包含馬匹資料的 tr
            rows = await page.locator("tr").all()
            logging.info(f"偵測到網頁行數: {len(rows)}")

            for row in rows:
                try:
                    cells = await row.locator("td").all()
                    # 排位表列數通常較多 (約 10 欄以上)
                    if len(cells) >= 6:
                        # 取得第一欄(馬號)的文字
                        no_raw = (await cells[0].inner_text()).strip()
                        # 只要是 1-14 之間的數字就是馬匹
                        if no_raw.isdigit() and 1 <= int(no_raw) <= 14:
                            name = (await cells[2].inner_text()).strip()
                            jockey = (await cells[3].inner_text()).strip()
                            trainer = (await cells[4].inner_text()).strip()
                            draw = (await cells[5].inner_text()).strip()
                            
                            entries_data[no_raw] = {
                                "name": name.split('(')[0].strip(), # 去除 (B/H) 等裝備字眼
                                "jockey": jockey,
                                "trainer": trainer,
                                "draw": draw
                            }
                except:
                    continue
            
            logging.info(f"成功抓取馬匹數量: {len(entries_data)}")
                
        except Exception as e:
            logging.error(f"抓取出錯: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    # 使用安全的 run 方式
    try:
        data = asyncio.run(fetch_entries())
    except:
        data = {}

    # 即使為空也要產出檔案，避免 git 報錯
    if not data:
        data = {"STATUS": "EMPTY", "TIME": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logging.info(f"--- 檔案已寫入 {DATA_FILE} ---")
