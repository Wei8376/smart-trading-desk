import datetime
import requests
from app import app, db, StockPrice

def run_official_twse_crawler():
    # 我們的目標監控清單
    stock_list = ['2330', '2308', '0050', '00981A', '00403A', '006208']
    
    # 全自動抓取執行當天（今天）的正確西元日期
    today_date = datetime.date.today()
    date_str_twse = today_date.strftime('%Y%m%d') # "20260519"

    print(f"=== [系統啟動] 開始全自動抓取證交所官方 {today_date} 盤後大數據 ===")

    with app.app_context():
        for stock_id in stock_list:
            # 證交所官方個股當日盤後精準 API
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str_twse}&stockNo={stock_id}"
            
            try:
                response = requests.get(url, timeout=10)
                res_data = response.json()
                
                # 驗證證交所是否有成功回傳資料
                if res_data.get('stat') != 'OK' or 'data' not in res_data:
                    print(f" ⚠️ 代號 {stock_id}：證交所今日尚未公告或此個股無數據")
                    continue
                
                # 自動從證交所標題拆解出正確的股票名稱
                stock_name = res_data.get('title', '').split(' ')[2] if 'title' in res_data else "台灣個股"
                
                # 證交所的 data 陣列包含了當月所有的交易日，我們直接提取最後一筆（也就是今天最新收盤日）
                latest_market_row = res_data['data'][-1]
                
                # 證交所官方欄位索引：[3]開盤價, [4]最高價, [5]最低價, [6]收盤價
                # 清除可能夾帶的逗號（例如千元股的 1,000）並轉為浮點數
                open_p = float(latest_market_row[3].replace(',', ''))
                high_p = float(latest_market_row[4].replace(',', ''))
                low_p = float(latest_market_row[5].replace(',', ''))
                close_p = float(latest_market_row[6].replace(',', ''))
                
                # 檢查資料庫是否今天已經有這檔股票的紀錄了（避免重複塞入造成幽靈橫軸）
                existing_record = StockPrice.query.filter_by(
                    stock_id=stock_id, 
                    created_at=datetime.datetime.combine(today_date, datetime.time(13, 30, 0))
                ).first()
                
                if existing_record:
                    # 如果今天抓過，直接更新它，確保數據絕對精準
                    existing_record.open_price = open_p
                    existing_record.high_price = high_p
                    existing_record.low_price = low_p
                    existing_record.close_price = close_p
                    print(f" 🔄 數據更新 -> {stock_name} ({stock_id}) | 開:{open_p} 收:{close_p}")
                else:
                    # 如果今天還沒抓過，新建一筆紀錄
                    new_record = StockPrice(
                        stock_id=stock_id,
                        stock_name=stock_name,
                        open_price=open_p,
                        high_price=high_p,
                        low_price=low_p,
                        close_price=close_p,
                        created_at=datetime.datetime.combine(today_date, datetime.time(13, 30, 0))
                    )
                    db.session.add(new_record)
                    print(f" 💾 新增存檔 -> {stock_name} ({stock_id}) | 開:{open_p} 收:{close_p}")
                    
                db.session.commit()
                
            except Exception as e:
                db.session.rollback()
                print(f" ❌ 處理代號 {stock_id} 時發生異常錯誤: {str(e)}")
                
        print("=== [大功告成] 全數監控股票官方真實數據自動同步完畢！ ===")

if __name__ == '__main__':
    run_official_twse_crawler()