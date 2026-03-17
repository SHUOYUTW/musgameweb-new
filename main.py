import os
import re
import socket
import urllib.parse
from flask import Flask, render_template, abort, request
from flask_sqlalchemy import SQLAlchemy

# --- 1. 強制使用 IPv4 修正 (解決本地與雲端連線 Supabase 的網路問題) ---
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

app = Flask(__name__)

# --- 2. 資料庫連線配置 ---
# 優先讀取環境變數，本地開發若無設定則使用備用字串
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    # 這是你測試成功的連線資訊
    DB_USER = "postgres.fsdrnmwvsngbaasiriou"
    DB_PASSWORD = "Eason123778487" 
    DB_HOST = "aws-1-ap-south-1.pooler.supabase.com" 
    DB_PORT = "6543"
    DB_NAME = "postgres"
    safe_password = urllib.parse.quote_plus(DB_PASSWORD)
    db_url = f"postgresql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 修正協定頭並確保 SSL 參數
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
if "sslmode" not in db_url:
    db_url += "&sslmode=require" if "?" in db_url else "?sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 1800}

# 修正 NameError：確保從模組引入後直接使用 SQLAlchemy 類別
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

# --- 4. 輔助功能：圖片路徑檢查 ---
def is_local_image(image_name):
    """檢查本地 static/images/ 是否存在該檔案"""
    if not image_name: return False
    local_path = os.path.join(app.root_path, 'static', 'images', image_name)
    return os.path.exists(local_path)

# --- 5. 路由邏輯 ---
@app.route('/')
def index():
    try:
        query = request.args.get('search', '')
        games = GameInfo.query.filter(GameInfo.game_name.ilike(f"%{query}%")).all() if query else GameInfo.query.all()
        for g in games:
            g.use_local = is_local_image(g.image_url)
        return render_template('index.html', games=games, search_query=query)
    except Exception as e:
        print(f"Database Error: {e}")
        return f"資料庫讀取異常：{e}"

@app.route('/price/<string:g_name>')
def price(g_name):
    info = GameInfo.query.filter_by(game_name=g_name).first()
    items = GameData.query.filter_by(game_name=g_name).all()
    if not items: abort(404)

    if info: info.use_local = is_local_image(info.image_url)
    for item in items: item.use_local = is_local_image(item.item_image)

    def natural_sort_key(item):
        numbers = re.findall(r'\d+', item.item_name)
        num = int(numbers[0]) if numbers else 0
        return (item.item_name.replace(str(num), ''), num, item.price)
    
    return render_template('price.html', game_name=g_name, items=sorted(items, key=natural_sort_key), game_info=info)

if __name__ == '__main__':
    # 本地測試使用 5000 埠
    app.run(host='127.0.0.1', port=5000, debug=True)
