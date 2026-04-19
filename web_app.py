from flask import Flask, render_template, request # request 추가
from data_manager import load_data

app = Flask(__name__)

SHOP_ITEMS = {
    "1": {"name": "🔥 전설의 검", "price": 50000},
    "2": {"name": "🛡️ 초보자 방패", "price": 10000},
    "3": {"name": "🧪 마나 포션", "price": 2000},
    "4": {"name": "💎 무지개 보석", "price": 100000}
}

@app.route('/')
def home():
    data = load_data()
    # 주소창에 localhost:5000/?user_id=123456 처럼 입력하면 해당 유저 정보를 가져옴
    user_id = request.args.get('user_id') 
    
    if user_id and user_id in data:
        user_info = data[user_id]
        current_user = {"id": user_id, "balance": user_info['balance']}
    else:
        # 아이디가 없거나 잘못됐을 때 기본값
        current_user = {"id": "로그인 필요", "balance": 0}

    return render_template('index.html', user=current_user, items=SHOP_ITEMS)

def run_web():
    app.run(port=5000, debug=False, use_reloader=False)