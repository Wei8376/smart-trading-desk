import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
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
    app.run(host='0.0.0.0', port=5001, debug=True)