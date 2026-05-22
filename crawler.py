import os
import sys
import requests
from datetime import datetime, timedelta
from app import app, db, StockPrice

STOCKS = {
    "2330": "台積電",
    "2308": "台達電",
    "0050": "元大台灣50",
    "006208": "富邦台50",
    "00981A": "主動統一台股增長",
    "00403A": "主動統一升級50"
}

def fetch_twse_data(date_str):
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={date_str}&type=ALLBUT0999&response=json"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return None
        data = response.json()
        if data.get("stat") != "OK":
            return None
        return data
    except Exception:
        return None

def parse_and_save(data, date_str):
    target_date = datetime.strptime(date_str, "%Y%m%d").date()
    any_saved = False
    
    # 擴大搜尋範圍 (tables 7 到 10)，防禦證交所隨意更動表格順序
    for table_idx in range(7, 11):
        if "tables" in data and len(data["tables"]) > table_idx:
            table = data["tables"][table_idx]
            fields = table.get("fields", [])
            table_data = table.get("data", [])
            
            try:
                # 尋找必須的欄位
                id_idx = fields.index("證券代號")
                open_idx = fields.index("開盤價")
                high_idx = fields.index("最高價")
                low_idx = fields.index("最低價")
                close_idx = fields.index("收盤價")
                
                # 如果欄位都齊全，就開始比對資料
                for row in table_data:
                    sid = row[id_idx].strip()
                    if sid in STOCKS:
                        # 只要有任何一筆成功寫入，就標記為 True
                        if save_row_to_db(sid, row, open_idx, high_idx, low_idx, close_idx, target_date):
                            any_saved = True
            except ValueError:
                # 如果這個表格缺少某些欄位 (例如沒有開盤價)，直接跳過，不引發 Rollback
                continue
                
    return any_saved

def save_row_to_db(sid, row, open_idx, high_idx, low_idx, close_idx, target_date):
    try:
        # 清理字串中的逗號並轉為浮點數
        op = float(row[open_idx].replace(',', '').strip())
        hi = float(row[high_idx].replace(',', '').strip())
        lo = float(row[low_idx].replace(',', '').strip())
        cl = float(row[close_idx].replace(',', '').strip())
    except ValueError:
        return False

    # 檢查是否已經存在 (使用正確的 created_at 欄位)
    exists = StockPrice.query.filter_by(stock_id=sid, created_at=target_date).first()
    if not exists:
        new_price = StockPrice(
            stock_id=sid,
            stock_name=STOCKS[sid],
            created_at=target_date,
            open_price=op,
            high_price=hi,
            low_price=lo,
            close_price=cl
        )
        db.session.add(new_price)
        print(f" 💾 成功匯入 -> {STOCKS[sid]} ({sid}) | 日期: {target_date}")
        return True
    return False

def run_crawler(target_date_str):
    print(f"🚀 開始檢查 {target_date_str} 證交所官方數據...")
    json_data = fetch_twse_data(target_date_str)
    if not json_data:
        print(f" 提示：{target_date_str} 未取得資料")
        return False
        
    with app.app_context():
        any_saved = parse_and_save(json_data, target_date_str)
        if any_saved:
            db.session.commit()
            print(f" ✅ 成功：{target_date_str} 數據已確實 Commit 同步至資料庫！")
        else:
            db.session.rollback()
            print(f" 狀態：{target_date_str} 資料庫已有資料或無新數據，跳過。")
        return True

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--backfill":
        try:
            days_to_backfill = int(sys.argv[2])
            print(f"🔄 啟動自訂歷史回溯：準備檢查過去 {days_to_backfill} 天的資料...")
            end_date = datetime.today()
            for i in range(days_to_backfill, -1, -1):
                current_check_date = (end_date - timedelta(days=i)).strftime("%Y%m%d")
                run_crawler(current_check_date)
            print(" 歷史回溯結束！")
        except ValueError:
            print("❌ 參數錯誤！")
            
    else:
        print("⚡ 啟動日常智能同步模式...")
        today = datetime.today()
        # 檢查過去三天
        for i in range(2, -1, -1):
            check_date_str = (today - timedelta(days=i)).strftime("%Y%m%d")
            run_crawler(check_date_str)
        print(" 數據同步檢索完成！")