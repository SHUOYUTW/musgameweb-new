import os
import re
import socket
import urllib.parse
from flask import Flask, render_template, abort, request
from flask_sqlalchemy import SQLAlchemy

# --- 1. 強制使用 IPv4 修正 (必須放在最前面) ---
# 解決 Render 連線 Supabase 時常見的 Network is unreachable (IPv6) 問題
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

app = Flask(__name__)

# --- 2. 資料庫連線配置 ---
# 優先讀取 Render 後台的 DATABASE_URL 環境變數
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    # 如果環境變數讀不到，才使用你提供的備用連線資訊
    DB_USER = "postgres.fsdrnmwvsngbaasiriou"
    DB_PASSWORD = "Eason123778487" 
    DB_HOST = "aws-1-ap-south-1.pooler.supabase.com" 
    DB_PORT = "6543"
    DB_NAME = "postgres"
    safe_password = urllib.parse.quote_plus(DB_PASSWORD)
    db_url = f"postgresql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 修復協定頭 (Render 有時會給 postgres://)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# 確保加上 sslmode=require 參數
if "sslmode" not in db_url:
    separator = "&" if "?" in db_url else "?"
    db_url += f"{separator}sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}

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
        if query:
            games = GameInfo.query.filter(GameInfo.game_name.ilike(f"%{query}%")).all()
        else:
            games = GameInfo.query.all()
        return render_template('index.html', games=games, search_query=query)
    except Exception as e:
        # 正式環境下，建議也印出 e 到 Logs 方便除錯
        print(f"Database Error: {e}")
        return f"資料庫讀取異常，請稍後再試。 詳細錯誤已紀錄。"

@app.route('/price/<string:g_name>')
def price(g_name):
    info = GameInfo.query.filter_by(game_name=g_name).first()
    items = GameData.query.filter_by(game_name=g_name).all()
    
    if not items:
        abort(404)

    def natural_sort_key(item):
        numbers = re.findall(r'\d+', item.item_name)
        num = int(numbers[0]) if numbers else 0
        return (item.item_name.replace(str(num), ''), num, item.price)

    sorted_items = sorted(items, key=natural_sort_key)
    return render_template('price.html', game_name=g_name, items=sorted_items, game_info=info)

# --- 5. 啟動入口 (必須放在最後) ---
if __name__ == '__main__':
    # Render 環境必須讀取 PORT 變數，host 必須是 0.0.0.0
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
