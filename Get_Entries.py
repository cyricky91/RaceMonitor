import os
import asyncio
import json
import logging
from playwright.async_api import async_playwright
import time

DATA_FILE = "today_entries.json"
logging.basicConfig(level=logging.INFO)

async def fetch_entries():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        entries_data = {}
        try:
            logging.info("正在連線至馬會排位表頁面...")
            # 前往排位表，等待網路閒置
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="domcontentloaded", timeout=60000)
            
            # 給予額外時間讓 JavaScript 渲染表格
            await asyncio.sleep(5)
            
            # 直接針對所有 tr 進行深度掃描
            rows = await page.locator("tr").all()
            logging.info(f"偵測到網頁中共有 {len(rows)} 行數據")

            for row in rows:
                try:
                    # 獲取該行所有文字內容
                    text_content = await row.inner_text()
                    cells = await row.locator("td").all()
                    
                    if len(cells) >= 6:
                        raw_no = (await cells[0].inner_text()).strip()
                        # 修正判斷邏輯：有些馬號可能帶有換行或空格
                        no = "".join(filter(str.isdigit, raw_no))
                        
                        if no and int(no) < 20: # 馬號通常不會超過 14-15
                            entries_data[no] = {
                                "name": (await cells[2].inner_text()).strip().split('(')[0].strip(),
                                "jockey": (await cells[3].inner_text()).strip(),
                                "trainer": (await cells[4].inner_text()).strip(),
                                "draw": (await cells[5].inner_text()).strip()
                            }
                except:
                    continue
            
            logging.info(f"最終解析結果：抓取到 {len(entries_data)} 匹馬")
                
        except Exception as e:
            logging.error(f"執行過程出錯: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    # 修正 asyncio 呼叫方式，避免 RuntimeError
    try:
        data = asyncio.run(fetch_entries())
    except Exception as e:
        logging.error(f"Asyncio 運行失敗: {e}")
        data = {}

    # 即使沒抓到數據，也生成一個帶有時間戳的檔案
    if not data:
        logging.warning("警告：未抓取到數據，生成空結構檔案。")
        data = {"STATUS": "EMPTY", "UPDATE_TIME": time.strftime("%Y-%m-%d %H:%M:%S")}

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logging.info(f"--- 檔案已成功寫入 {DATA_FILE} ---")
