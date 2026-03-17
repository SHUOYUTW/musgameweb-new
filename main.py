import os
import re
import socket
import urllib.parse
from flask import Flask, render_template, abort, request
from flask_sqlalchemy import SQLAlchemy

# --- 1. IPv4 強制修正 (解決 Render 連線 Supabase 的網路問題) ---
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

app = Flask(__name__)

# --- 2. 資料庫連線配置 (直接寫入資訊) ---
DB_USER = "postgres.fsdrnmwvsngbaasiriou"
DB_PASSWORD = "Eason123778487" 
DB_HOST = "aws-1-ap-south-1.pooler.supabase.com" 
DB_PORT = "6543"
DB_NAME = "postgres"

# 自動處理密碼特殊字元並組合 URI
safe_password = urllib.parse.quote_plus(DB_PASSWORD)
default_uri = f"postgresql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"

# 優先讀取環境變數，若無則使用上方寫死的字串
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", default_uri)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 1800}

# 修正 SQLAlchemy 初始化方式
db = SQLAlchemy(app)

# --- 3. 資料庫模型 ---
class GameInfo(db.Model):
    __tablename__ = 'game_info'
    id = db.Column(db.Integer, primary_key=True)
    game_name = db.Column(db.String(100), unique=True, nullable=False)
    image_url = db.Column(db.String(500))

class GameData(db.Model):
    __tablename__ = 'gamedata'
    id = db.Column(db.Integer, primary_key=True)
    game_name = db.Column(db.String(100), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    item_image = db.Column(db.String(500))

# --- 4. 路由邏輯 ---
@app.route('/')
def index():
    try:
        query = request.args.get('search', '')
        # 搜尋邏輯
        if query:
            games = GameInfo.query.filter(GameInfo.game_name.ilike(f"%{query}%")).all()
        else:
            games = GameInfo.query.all()
        return render_template('index.html', games=games, search_query=query)
    except Exception as e:
        return f"資料庫讀取異常：{e}"

@app.route('/price/<string:g_name>')
def price(g_name):
    # 根據遊戲名稱抓取資料
    info = GameInfo.query.filter_by(game_name=g_name).first()
    items = GameData.query.filter_by(game_name=g_name).all()
    
    if not items:
        abort(404)

    # 自然排序邏輯 (確保面額由小到大)
    def natural_sort_key(item):
        numbers = re.findall(r'\d+', item.item_name)
        num = int(numbers[0]) if numbers else 0
        return (item.item_name.replace(str(num), ''), num, item.price)
    
    sorted_items = sorted(items, key=natural_sort_key)
    return render_template('price.html', game_name=g_name, items=sorted_items, game_info=info)

if __name__ == '__main__':
    # 支援 Render 分配的 PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
