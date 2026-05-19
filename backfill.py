import datetime
import requests
from dotenv import load_dotenv
from app import app, db, StockPrice

load_dotenv()

def backfill_from_official_twse():
    stock_list = ['2330', '2308', '0050', '00981A', '00403A', '006208']
    
    # 5/18 與 5/19 兩天的日期字串
    target_dates = ['20260518', '20260519']

    print("=== [系統啟動] 開始強行洗牌資料庫，並自證交所下載精準歷史數據 ===")

    with app.app_context():
        # 1. 物理清空舊數據，確保幽靈橫軸與錯誤價格徹底消失
        db.session.query(StockPrice).delete()
        db.session.commit()
        print(" 🧹 資料庫已全數清空完畢")

        # 2. 依序撈取這兩天官方數據
        for date_str in target_dates:
            target_date = datetime.datetime.strptime(date_str, '%Y%m%d').date()
            
            for stock_id in stock_list:
                url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_id}"
                
                try:
                    response = requests.get(url, timeout=10)
                    res_data = response.json()
                    
                    if res_data.get('stat') != 'OK' or 'data' not in res_data:
                        continue
                    
                    stock_name = res_data.get('title', '').split(' ')[2] if 'title' in res_data else "台灣個股"
                    
                    # 尋找對應日期的那一個數據列
                    target_row = None
                    for row in res_data['data']:
                        # 轉換民國日期 (例如 "115/05/18")
                        date_parts = row[0].split('/')
                        year_ce = int(date_parts[0]) + 1911
                        row_date_str = f"{year_ce}{date_parts[1]}{date_parts[2]}"
                        
                        if row_date_str == date_str:
                            target_row = row
                            break
                    
                    if target_row:
                        open_p = float(target_row[3].replace(',', ''))
                        high_p = float(target_row[4].replace(',', ''))
                        low_p = float(target_row[5].replace(',', ''))
                        close_p = float(target_row[6].replace(',', ''))
                        
                        new_record = StockPrice(
                            stock_id=stock_id,
                            stock_name=stock_name,
                            open_price=open_p,
                            high_price=high_p,
                            low_price=low_p,
                            close_price=close_p,
                            created_at=datetime.datetime.combine(target_date, datetime.time(13, 30, 0))
                        )
                        db.session.add(new_record)
                        print(f" ✅ 成功寫入 -> {date_str[4:6]}/{date_str[6:]} {stock_name} ({stock_id}) | 收:{close_p}")
                        
                except Exception as e:
                    print(f" ❌ 處理 {stock_id} 於 {date_str} 出錯: {str(e)}")
                    
            db.session.commit()
            
        print("\n=== [完美收工] 5/18 與 5/19 證交所官方真實價格已全數自動校正歸位！ ===")

if __name__ == '__main__':
    backfill_from_official_twse()