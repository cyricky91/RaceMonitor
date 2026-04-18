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
        page = await browser.new_page()
        entries_data = {}
        try:
            # 增加 Referer 模擬正常點擊進入
            await page.set_extra_http_headers({"Referer": "https://racing.hkjc.com/"})
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="networkidle")
            
            # 等待主要的表格標籤出現
            await page.wait_for_selector("table", timeout=10000)
            
            # 抓取表格中所有包含馬號的單元格
            rows = await page.query_selector_all("tr")
            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) >= 6:
                    raw_no = await cells[0].inner_text()
                    no = "".join(filter(str.isdigit, raw_no.strip()))
                    if no and 1 <= int(no) <= 14:
                        entries_data[no] = {
                            "name": (await cells[2].inner_text()).strip().split('(')[0].strip(),
                            "jockey": (await cells[3].inner_text()).strip(),
                            "trainer": (await cells[4].inner_text()).strip(),
                            "draw": (await cells[5].inner_text()).strip()
                        }
        except Exception as e:
            logging.error(f"排位表抓取出錯: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    data = asyncio.run(fetch_entries())
    output = {"update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "entries": data}
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print(f"成功寫入 {len(data)} 匹馬")
