import requests
from bs4 import BeautifulSoup
import logging
import os
import json

# --- 配置區 ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
URL = "https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=ch"
DATA_FILE = "last_odds.json"

logging.basicConfig(level=logging.INFO)

def send_telegram_msg(message):
    if not TOKEN: return
    target_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(target_url)

def load_previous_odds():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_current_odds(odds):
    with open(DATA_FILE, 'w') as f:
        json.dump(odds, f)

def get_live_odds():
    # 注意：這裡可能需要改用 Selenium 才能抓到實際數字
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        current_race_odds = {}
        
        # 這裡需要根據馬會實際 HTML 結構精確定位
        # 提示：馬會現在很多數據在 <iframe> 或 AJAX 請求中
        horses = soup.select('.horse_item') 
        for horse in horses:
            try:
                no = horse.select_one('.horse_no').text.strip()
                win_odds = float(horse.select_one('.win_odds').text.strip())
                current_race_odds[no] = win_odds
            except: continue
        return current_race_odds
    except Exception as e:
        logging.error(f"抓取失敗: {e}")
        return {}

def run_once():
    logging.info("執行單次監控檢查...")
    last_odds = load_previous_odds()
    current_odds = get_live_odds()
    
    if not current_odds:
        logging.warning("抓不到數據。如果是 GitHub Actions，可能需要處理瀏覽器環境。")
        return

    for no, odds in current_odds.items():
        if no in last_odds:
            old_odds = last_odds[no]
            drop_rate = (old_odds - odds) / old_odds
            if drop_rate >= 0.2:
                send_telegram_msg(f"⚠️ 落飛警報：{no}號，賠率由 {old_odds} 跌至 {odds}")

    save_current_odds(current_odds)

if __name__ == "__main__":
    run_once()
