import os
import asyncio
import json
import logging
from playwright.async_api import async_playwright

# 馬會排位表 URL (以當日賽事為準)
URL = "https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx" # 建議改用排位表專用連結
DATA_FILE = "today_entries.json"

logging.basicConfig(level=logging.INFO)

async def fetch_entries():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        page = await context.new_page()
        
        entries_data = {}
        try:
            # 這裡以馬會「排位表」頁面為目標
            await page.goto("https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx", wait_until="networkidle")
            
            # 取得所有場次
            # 注意：這裡需要遍歷場次，以下為單場示範邏輯
            rows = await page.locator(".ltable tr").all()
            for row in rows:
                try:
                    # 抓取：馬號、馬名、檔位、騎師、練馬師
                    cells = await row.locator("td").all()
                    if len(cells) > 5:
                        no = await cells[0].inner_text()
                        horse_name = await cells[2].inner_text()
                        jockey = await cells[3].inner_text()
                        trainer = await cells[4].inner_text()
                        draw = await cells[5].inner_text()
                        
                        entries_data[no.strip()] = {
                            "name": horse_name.strip(),
                            "jockey": jockey.strip(),
                            "trainer": trainer.strip(),
                            "draw": draw.strip()
                        }
                except: continue
            
            logging.info(f"成功儲存 {len(entries_data)} 匹馬的排位資訊")
        except Exception as e:
            logging.error(f"抓取排位表失敗: {e}")
        finally:
            await browser.close()
        return entries_data

if __name__ == "__main__":
    data = asyncio.run(fetch_entries())
    if data:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
