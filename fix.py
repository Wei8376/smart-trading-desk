from app import app, db, StockPrice
from crawler import run_crawler
from datetime import datetime, timedelta

with app.app_context():
    StockPrice.query.filter(StockPrice.created_at >= '2026-05-20').delete()
    db.session.commit()

    today = datetime.today()
    for i in range(2, -1, -1):
        check_date_str = (today - timedelta(days=i)).strftime("%Y%m%d")
        run_crawler(check_date_str)