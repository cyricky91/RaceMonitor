import os
import asyncio
import json
import logging
from playwright.async_api import async_playwright

# 檔案儲存路徑
DATA_FILE = "today_entries.json"

logging.basicConfig(level=logging.INFO)

async def fetch_entries():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 模擬桌面瀏覽器
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        entries_data = {}
        try:
            logging.info("正在連線至馬會排位表頁面...")
            # 直接前往排位表頁面
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="networkidle", timeout=60000)
            
            # 【關鍵】馬會數據通常在名為 'main' 或特定的 frame 裡
            # 我們先等待表格元素出現
            try:
                await page.wait_for_selector(".ltable", timeout=20000)
            except:
                logging.warning("找不到 .ltable，嘗試抓取所有表格...")

            # 抓取所有符合排位表結構的行
            # 馬會的排位表行通常包含特定的 class 或結構
            rows = await page.locator("tr").all()
            
            for row in rows:
                try:
                    cells = await row.locator("td").all()
                    # 排位表標準欄位：0:馬號, 2:馬名, 3:騎師, 4:練馬師, 5:檔位
                    if len(cells) >= 6:
                        no_text = await cells[0].inner_text()
                        name_text = await cells[2].inner_text()
                        jockey_text = await cells[3].inner_text()
                        trainer_text = await cells[4].inner_text()
                        draw_text = await cells[5].inner_text()
                        
                        no = no_text.strip()
                        # 確保第一欄是馬號（數字）
                        if no.isdigit():
                            entries_data[no] = {
                                "name": name_text.strip(),
                                "jockey": jockey_text.strip(),
                                "trainer": trainer_text.strip(),
                                "draw": draw_text.strip()
                            }
                except Exception as e:
                    continue
            
            if not entries_data:
                logging.error("解析結束，但未抓取到任何有效馬匹數據。")
            else:
                logging.info(f"成功解析 {len(entries_data)} 匹馬的資訊。")
                
        except Exception as e:
            logging.error(f"執行過程出錯: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    data = asyncio.run(fetch_entries())
    if data:
        # 確保檔案寫在當前工作目錄
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logging.info(f"--- 檔案已成功寫入 {DATA_FILE} ---")
    else:
        logging.error("--- 數據為空，取消寫入檔案 ---")
