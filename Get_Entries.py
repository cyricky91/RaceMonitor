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
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="networkidle")
            await asyncio.sleep(3)
            rows = await page.locator("tr").all()
            for row in rows:
                cells = await row.locator("td").all()
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
            logging.error(f"出錯: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    data = asyncio.run(fetch_entries())
    output = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "entries": data
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print(f"成功寫入 {len(data)} 匹馬")
