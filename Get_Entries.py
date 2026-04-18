import requests
import json
import logging
import re
from datetime import datetime

DATA_FILE = "today_entries.json"
logging.basicConfig(level=logging.INFO)

def fetch_all_entries():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    entries_data = {}
    
    # 使用「排位簡表」URL，這個頁面結構最穩定，且一次顯示所有場次
    url = "https://racing.hkjc.com/racing/information/Chinese/Racing/Entries.aspx"
    
    try:
        logging.info("正在抓取全場次排位表...")
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            # 這是針對「所有場次」表格的解析邏輯
            # 匹配：馬號 (td), 馬名 (a href), 騎師 (td), 練馬師 (td), 檔位 (td)
            # 這裡使用更寬鬆的匹配，確保不會因為換行而失敗
            content = resp.text
            
            # 抓取所有包含馬名鏈接的部分
            # 格式通常為：HorseId=XXXX">馬名</a>
            matches = re.findall(r'HorseId=.*?">([^<]+)</a>', content)
            
            for i, name in enumerate(matches):
                # 由於這類簡表通常按場次順序排列
                # 我們先保證馬名被存入，Key 使用序號
                entries_data[str(i+1)] = {
                    "name": name.strip().split('(')[0],
                    "jockey": "-", 
                    "trainer": "-", 
                    "draw": "-"
                }
            
            logging.info(f"✅ 成功！全場次共抓取到 {len(entries_data)} 匹馬。")
    except Exception as e:
        logging.error(f"抓取失敗: {e}")
        
    return entries_data

if __name__ == "__main__":
    data = fetch_all_entries()
    output = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "horse_count": len(data),
        "entries": data
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
