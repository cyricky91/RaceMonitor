import os
import asyncio
import json
import logging
from playwright.async_api import async_playwright

DATA_FILE = "today_entries.json"
logging.basicConfig(level=logging.INFO)

async def fetch_entries():
    async with async_playwright() as p:
        # 使用更大的視窗尺寸，確保所有表格都加載
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        entries_data = {}
        try:
            logging.info("正在連線至馬會排位表頁面...")
            # 增加等待時間，確保 JavaScript 完全執行
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="networkidle", timeout=60000)
            
            # 嘗試切換到可能存在的 iframe (馬會常用手法)
            frames = page.frames
            target_frame = page
            for f in frames:
                if "racing" in f.url or "Entries" in f.url:
                    target_frame = f
                    break

            # 等待表格出現，改用更通用的標籤
            await target_frame.wait_for_timeout(5000) # 強制等待 5 秒讓數據加載
            
            # 抓取所有 tr 進行篩選
            rows = await target_frame.locator("tr").all()
            logging.info(f"偵測到網頁中共有 {len(rows)} 行數據")

            for row in rows:
                try:
                    cells = await row.locator("td").all()
                    if len(cells) >= 6:
                        no_text = (await cells[0].inner_text()).strip()
                        # 只要第一欄是數字，就是我們要的馬匹行
                        if no_text.isdigit():
                            entries_data[no_text] = {
                                "name": (await cells[2].inner_text()).strip(),
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
    data = asyncio.run(fetch_entries())
    
    # 測試機制：即使沒抓到數據，也生成一個「結構完整」的檔案，防止下一個腳本崩潰
    if not data:
        logging.warning("警告：今日可能無賽事排位表。")
        data = {"STATUS": "NO_ENTRIES_FOUND", "LAST_UPDATE": str(asyncio.get_event_loop().time())}

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logging.info(f"--- 檔案已寫入 {DATA_FILE} ---")
