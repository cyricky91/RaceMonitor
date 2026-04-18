import asyncio
import json
import logging
from playwright.async_api import async_playwright
from datetime import datetime

DATA_FILE = "today_entries.json"
logging.basicConfig(level=logging.INFO)

async def fetch_entries():
    async with async_playwright() as p:
        # 使用手機版的 User-Agent
        browser = await p.chromium.launch(headless=True)
        iphone = p.devices['iPhone 13']
        context = await browser.new_context(**iphone)
        page = await context.new_page()
        entries_data = {}
        
        try:
            logging.info("切換至手機版排位表...")
            # 手機版排位表路徑
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
            
            # 手機版結構通常直接用表格
            rows = await page.locator("table tr").all()
            for row in rows:
                text = await row.inner_text()
                # 過濾出包含馬匹編號的列
                parts = text.split('\t')
                if len(parts) >= 3 and parts[0].isdigit():
                    no = parts[0]
                    name = parts[2].split('(')[0].strip()
                    entries_data[no] = {"name": name, "jockey": "即時", "trainer": "即時", "draw": "-"}
            
            if not entries_data:
                # 備用方案：如果手機版失敗，直接從賽事日期列表硬抓
                logging.info("嘗試備用解析方案...")
                content = await page.content()
                import re
                # 匹配馬匹鏈接中的編號和文字
                found = re.findall(r'HorseId=.*?">(\d+)\s+(.*?)</a>', content)
                for f_no, f_name in found:
                    entries_data[f_no] = {"name": f_name.strip(), "jockey": "-", "trainer": "-", "draw": "-"}

        except Exception as e:
            logging.error(f"抓取失敗: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    data = asyncio.run(fetch_entries())
    output = {"update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "entries": data}
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print(f"最終抓取到 {len(data)} 匹馬")
