import os
from google import genai
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

import os

db_url = os.getenv("DATABASE_URL")

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///smart_trading.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class EmotionRecord(db.Model):
    __tablename__ = 'emotion_records'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class StockPrice(db.Model):
    __tablename__ = 'stock_prices'
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.String(10), nullable=False)
    stock_name = db.Column(db.String(50), nullable=False)
    open_price = db.Column(db.Float, nullable=False)   # 開盤價
    high_price = db.Column(db.Float, nullable=False)   # 最高價
    low_price = db.Column(db.Float, nullable=False)    # 最低價
    close_price = db.Column(db.Float, nullable=False)  # 收盤價
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

@app.route('/')
def dashboard():
    return render_template('dashboard.html')
# 初始化 Gemini AI 用戶端 (會自動讀取 .env 裡的 GEMINI_API_KEY)
ai_client = genai.Client()

@app.route('/api/ai-analysis')
def get_ai_analysis():
    try:
        # 從資料庫抓取最新的 6 筆數據（也就是今天我們關注的這 6 檔標的）
        latest_prices = db.session.query(StockPrice).order_by(StockPrice.created_at.desc()).limit(6).all()
        
        if not latest_prices:
            return jsonify({'status': 'error', 'message': '資料庫目前沒有數據，請先執行爬蟲抓取資料。'})
            
        # 把這 6 筆數據整理成文字，準備餵給 AI
        data_summary = ""
        for p in latest_prices:
            data_summary += f"{p.stock_name} ({p.stock_id}): 開 {p.open_price} | 高 {p.high_price} | 低 {p.low_price} | 收 {p.close_price}\n"
            
        # 這是你身為工程師「詠唱」給 AI 的指令 (Prompt)
        prompt = f"""
        你是溫暖、專業的資深金融投資策略師。
        請根據以下台股數據寫一篇 150-200 字的盤後智能心靈簡評。
        要求：
        1. 像對投資人說故事般解讀市場情緒，勿念流水帳。
        2. 語氣溫暖，點評主動型基金的選股思維。
        3. 結尾給予充滿人文氣息的鼓勵。
        
        {data_summary}
        """
        
        # 呼叫 Gemini 產生內容
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        return jsonify({'status': 'success', 'analysis': response.text})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/stock/<stock_id>', methods=['GET'])
def get_stock_data(stock_id):
    try:
        records = StockPrice.query.filter_by(stock_id=stock_id).order_by(StockPrice.created_at.asc()).all()
        
        ohlc_data = []
        for r in records:
            ohlc_data.append({
                # 確保只有 YYYY-MM-DD，絕對不要帶有任何空白或時分秒！
                "t": r.created_at.strftime('%Y-%m-%d'), 
                "o": r.open_price,
                "h": r.high_price,
                "l": r.low_price,
                "c": r.close_price
            })
            
        stock_name = records[0].stock_name if records else "未知股票"
        
        return jsonify({
            "status": "success",
            "stock_id": stock_id,
            "stock_name": stock_name,
            "data": ohlc_data
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
    # === 隱藏開關：自動建置資料庫與爬蟲 ===
import os
from flask import jsonify

@app.route('/api/setup-and-crawl')
def setup_and_crawl():
    try:
        db.create_all()
        os.system('python crawler.py --backfill 4')
        return jsonify({'status': 'success', 'message': 'Setup and crawl completed successfully.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})