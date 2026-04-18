import requests
import json
import logging
import re
from datetime import datetime

DATA_FILE = "today_entries.json"
logging.basicConfig(level=logging.INFO)

def fetch_entries():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://racing.hkjc.com/"
    }
    entries_data = {}
    
    # 嘗試兩個不同的數據源
    urls = [
        "https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx",
        "https://racing.hkjc.com/racing/information/chinese/Racing/Entries.aspx"
    ]
    
    for url in urls:
        try:
            logging.info(f"嘗試訪問：{url}")
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                # 匹配馬名：尋找包含 HorseId 的連結文字
                matches = re.findall(r'HorseId=.*?">(\d+)\s+([^<]+)</a>', resp.text)
                if not matches:
                    # 另一種可能的 HTML 格式
                    matches = re.findall(r'(\d+)\s+([\u4e00-\u9fa5]{2,4})', resp.text)
                
                for no, name in matches:
                    if no.isdigit() and 1 <= int(no) <= 14:
                        entries_data[no] = {"name": name.strip()}
            
            if entries_data: break # 抓到就停止
        except Exception as e:
            logging.error(f"訪問出錯: {e}")

    return entries_data

if __name__ == "__main__":
    data = fetch_entries()
    output = {"update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "entries": data}
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print(f"✅ 成功儲存 {len(data)} 匹馬匹資料庫")
