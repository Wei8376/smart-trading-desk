import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from app import app, db, StockPrice

load_dotenv()

def crawl_yahoo_stock(stock_id):
    if 'A' in stock_id or 'B' in stock_id:
        url = f"https://tw.stock.yahoo.com/quote/{stock_id}.TWO"
    else:
        url = f"https://tw.stock.yahoo.com/quote/{stock_id}.TW"
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"[{stock_id}] 網頁請求失敗，狀態碼：{response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        name_tag = soup.find('h1', class_='C($c-link-text)')
        stock_name = name_tag.text.strip() if name_tag else "未知股票"
        
        price_tag = soup.find('span', class_=['Fz(32px)', 'Fw(b)'])
        if not price_tag:
            price_tags = soup.find_all('span', class_=lambda c: c and 'Fz(32px)' in c)
            if price_tags:
                price_tag = price_tags[0]
                
        if price_tag:
            price_str = price_tag.text.replace(',', '').strip()
            price = float(price_str)
            return {"stock_id": stock_id, "stock_name": stock_name, "price": price}
        else:
            print(f"[{stock_id}] 找不到股價標籤")
            return None
            
    except Exception as e:
        print(f"[{stock_id}] 爬取過程發生錯誤: {str(e)}")
        return None

def save_stock_to_db(stock_data):
    if not stock_data:
        return
        
    try:
        new_price = StockPrice(
            stock_id=stock_data['stock_id'],
            stock_name=stock_data['stock_name'],
            price=stock_data['price']
        )
        db.session.add(new_price)
        db.session.commit()
        print(f" 成功存入資料庫 - [{stock_data['stock_id']} {stock_data['stock_name']}] 當前股價: {stock_data['price']}")
    except Exception as e:
        db.session.rollback()
        print(f" 資料庫寫入失敗: {str(e)}")

if __name__ == '__main__':
    print("=== 開始執行台股個股爬蟲 ===")
    
    with app.app_context():
        db.create_all()
        
        target_stocks = ['2330', '2308', '0050', '00981A', '00403A', '006208']
        
        for stock_id in target_stocks:
            print(f"\n正在爬取個股代號: {stock_id} ...")
            result = crawl_yahoo_stock(stock_id)
            save_stock_to_db(result)
        
    print("\n=== 爬蟲任務結束 ===")