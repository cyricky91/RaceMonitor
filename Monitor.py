import requests
from bs4 import BeautifulSoup
import time
import logging

# --- 配置區 ---
telegram_token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("CHAT_ID")
# 馬會賠率介面 URL (範例為獨贏賠率)
URL = "https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=ch"

# 設定落飛警報閾值 (例如賠率下跌超過 20%)
DROP_THRESHOLD = 0.2 

# 儲存上一次抓取的賠率
last_odds = {}

logging.basicConfig(level=logging.INFO)

def send_telegram_msg(message):
    target_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try:
        requests.get(target_url)
    except Exception as e:
        logging.error(f"Telegram 發送失敗: {e}")

def get_live_odds():
    """
    抓取馬會網頁賠率 (注意：馬會動態網頁可能需要處理 JavaScript，
    此處為基礎爬蟲邏輯，若抓不到建議改用 Selenium)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(URL, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    current_race_odds = {}
    
    # 這裡的 Selector 需要根據馬會網頁實際的 HTML 標籤不斷更新
    # 假設馬匹編號在 .horse_no，賠率在 .win_odds
    horses = soup.select('.horse_item') 
    for horse in horses:
        try:
            no = horse.select_one('.horse_no').text.strip()
            win_odds = float(horse.select_one('.win_odds').text.strip())
            current_race_odds[no] = win_odds
        except:
            continue
            
    return current_race_odds

def monitor():
    global last_odds
    logging.info("賽馬監控機器人已啟動...")
    
    while True:
        current_odds = get_live_odds()
        
        if not current_odds:
            logging.warning("未能獲取數據，等待下一輪...")
        else:
            for no, odds in current_odds.items():
                if no in last_odds:
                    old_odds = last_odds[no]
                    # 計算跌幅
                    drop_rate = (old_odds - odds) / old_odds
                    
                    if drop_rate >= DROP_THRESHOLD:
                        msg = f"⚠️ 【落飛警報】\n馬匹編號：{no}號\n原賠率：{old_odds}\n現賠率：{odds}\n跌幅：{drop_rate:.1%}"
                        print(msg)
                        send_telegram_msg(msg)
            
            last_odds = current_odds
            
        # 每 5 分鐘檢查一次（賽前建議縮短至 1 分鐘）
        time.sleep(300)

if __name__ == "__main__":
    monitor()
