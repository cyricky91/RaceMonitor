import asyncio
import json
import logging
from playwright.async_api import async_playwright
from datetime import datetime
import re

DATA_FILE = "today_entries.json"
logging.basicConfig(level=logging.INFO)

async def fetch_entries():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        entries_data = {}
        try:
            logging.info("開始強制掃描排位表...")
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5) # 硬性等待加載
            
            content = await page.content()
            # 使用正則表達式直接從源碼提取馬號和馬名
            # 匹配格式範例: <td>1</td>...<td>馬名</td>
            matches = re.findall(r'<td>(\d+)</td>.*?<td>.*?</td>.*?<td>(.*?)</td>', content, re.DOTALL)
            
            for match in matches:
                no, name_raw = match
                name = re.sub('<[^<]+?>', '', name_raw).strip().split('(')[0].strip()
                if 1 <= int(no) <= 14 and name:
                    entries_data[no] = {"name": name, "jockey": "待查", "trainer": "待查", "draw": "-"}
            
            logging.info(f"掃描結束，共發現 {len(entries_data)} 匹馬。")
        except Exception as e:
            logging.error(f"掃描失敗: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    data = asyncio.run(fetch_entries())
    output = {"update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "entries": data}
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
