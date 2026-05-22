import os
import sys
from datetime import datetime, timedelta
import yfinance as yf
from app import app, db, StockPrice

STOCKS = {
    "2330": "台積電",
    "2308": "台達電",
    "0050": "元大台灣50",
    "006208": "富邦台50",
    "00981A": "主動統一台股增長",
    "00403A": "主動統一升級50"
}

def save_row_to_db(sid, op, hi, lo, cl, target_date):
    try:
        op = float(op)
        hi = float(hi)
        lo = float(lo)
        cl = float(cl)
    except ValueError:
        return False

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
    print(f"🚀 開始檢查 {target_date_str} 數據...")
    target_date = datetime.strptime(target_date_str, "%Y%m%d").date()
    next_date = target_date + timedelta(days=1)
    
    any_saved = False
    
    with app.app_context():
        for sid in STOCKS.keys():
            yf_symbol = f"{sid}.TW"
            try:
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(start=target_date.strftime("%Y-%m-%d"), end=next_date.strftime("%Y-%m-%d"))
                
                if not hist.empty:
                    row = hist.iloc[0]
                    if save_row_to_db(sid, row['Open'], row['High'], row['Low'], row['Close'], target_date):
                        any_saved = True
            except Exception:
                continue
                
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
        for i in range(2, -1, -1):
            check_date_str = (today - timedelta(days=i)).strftime("%Y%m%d")
            run_crawler(check_date_str)
        print(" 數據同步檢索完成！")