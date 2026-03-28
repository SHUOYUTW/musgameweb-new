import os
import re
import socket
import urllib.parse
from flask import Flask, render_template, abort, request
from flask_sqlalchemy import SQLAlchemy

# --- 1. IPv4 強制修正 ---
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

app = Flask(__name__)

# --- 2. 資料庫連線配置 ---
DB_USER = "postgres.fsdrnmwvsngbaasiriou"
DB_PASSWORD = "Eason123778487" 
DB_HOST = "aws-1-ap-south-1.pooler.supabase.com" 
DB_PORT = "6543"
DB_NAME = "postgres"

safe_password = urllib.parse.quote_plus(DB_PASSWORD)
default_uri = f"postgresql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", default_uri)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 1800}

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
        return f"資料庫讀取異常：{e}"

# 短網址路由：/p/ID
@app.route('/p/<int:game_id>')
def price(game_id):
    info = GameInfo.query.get(game_id)
    if not info:
        abort(404)
        
    items = GameData.query.filter_by(game_name=info.game_name).all()
    
    def natural_sort_key(item):
        numbers = re.findall(r'\d+', item.item_name)
        num = int(numbers[0]) if numbers else 0
        return (item.item_name.replace(str(num), ''), num, item.price)
    
    sorted_items = sorted(items, key=natural_sort_key)
    return render_template('price.html', game_name=info.game_name, items=sorted_items, game_info=info)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
