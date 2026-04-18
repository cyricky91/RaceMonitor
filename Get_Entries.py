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
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        entries_data = {}
        try:
            logging.info("正在連線至馬會排位表頁面...")
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="load", timeout=60000)
            
            # 強制等待表格加載
            await page.wait_for_selector("table.ltable", timeout=20000)
            
            # 使用更精確的定位器抓取馬匹列
            rows = await page.locator("table.ltable tr").all()
            logging.info(f"偵測到網頁中共有 {len(rows)} 行數據")
            
            for row in rows:
                cells = await row.locator("td").all()
                if len(cells) >= 6:
                    no_text = await cells[0].inner_text()
                    no = "".join(filter(str.isdigit, no_text.strip()))
                    # 只抓取有效的馬號 (1-14)
                    if no and no.isdigit() and 1 <= int(no) <= 14:
                        entries_data[no] = {
                            "name": (await cells[2].inner_text()).strip().split('(')[0].strip(),
                            "jockey": (await cells[3].inner_text()).strip(),
                            "trainer": (await cells[4].inner_text()).strip(),
                            "draw": (await cells[5].inner_text()).strip()
                        }
            
            if not entries_data:
                logging.warning("警告：解析完成但未找到馬匹數據，今日可能無賽事。")
            else:
                logging.info(f"成功解析：抓取到 {len(entries_data)} 匹馬")
                
        except Exception as e:
            logging.error(f"解析失敗: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    data = asyncio.run(fetch_entries())
    output = {"update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "entries": data}
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
