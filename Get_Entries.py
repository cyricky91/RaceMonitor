import requests
import json
import logging
import re
from datetime import datetime

DATA_FILE = "today_entries.json"
logging.basicConfig(level=logging.INFO)

def fetch_entries():
    # 偽裝成一般的電腦瀏覽器
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8"
    }
    entries_data = {}
    try:
        logging.info("正在透過輕量請求訪問賽卡...")
        # 直接抓取今日賽卡頁面
        url = "https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # 使用正則表達式抓取馬匹名稱與編號
            # 馬會源碼範例: HorseId=XXXX">1 閃耀耀</a>
            matches = re.findall(r'HorseId=.*?">(\d+)\s+([^<]+)</a>', response.text)
            for no, name in matches:
                clean_name = name.strip().split('(')[0]
                entries_data[no] = {
                    "name": clean_name,
                    "jockey": "-", "trainer": "-", "draw": "-"
                }
            logging.info(f"解析完成！找到 {len(entries_data)} 匹馬。")
        else:
            logging.error(f"請求失敗，狀態碼: {response.status_code}")
    except Exception as e:
        logging.error(f"執行出錯: {e}")
    return entries_data

if __name__ == "__main__":
    data = fetch_entries()
    output = {"update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "entries": data}
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
