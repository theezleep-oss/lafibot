import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import threading
import requests
import asyncio
from flask import Flask, render_template, session, redirect, request, url_for
from flask_socketio import SocketIO
from datetime import datetime, timedelta

# ==========================================
# 1. 환경 설정 및 데이터 관리
# ==========================================
TOKEN = "MTQ5NTE0MzgyMDQzMjUxMTE4Ng.GfmTjs.-IR6EqqMommVTggLASMRZ8WMzjyIIfqgfRZtiI"
CLIENT_ID = "1495143820432511186"
CLIENT_SECRET = "XAH3KU_T9nZ1hfmetfIQ_Zm8YSFzX_6g"
REDIRECT_URI = "http://127.0.0.1:5000/callback"
GUILD_ID = 1495143356391755776
MY_GUILD = discord.Object(id=GUILD_ID)

app = Flask(__name__)
app.config['SECRET_KEY'] = "lafi_hub_premium_2026_key"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
socketio = SocketIO(app)

DATA_FILE = 'users.json'

MEMBERSHIP_THEMES = {
    "[일반] 파랭이": {"color": 0x5865F2, "multiplier": 1.0},
    "[골드] 파랭이": {"color": 0x1E90FF, "multiplier": 2.0},
    "[다이아몬드] 파랭이": {"color": 0x00BFFF, "multiplier": 3.0}
}

def load_data():
    if not os.path.exists(DATA_FILE): return {}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ==========================================
# 2. 디스코드 봇 클래스
# ==========================================
class LafiBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
        print(f"✅ 서버 명령어 동기화 완료")

bot = LafiBot()

@bot.event
async def on_ready():
    print(f"🤖 시스템 로그인 성공: {bot.user.name}")

# ==========================================
# 3. 유저 명령어
# ==========================================
@bot.tree.command(name="출석체크", description="일일 보상을 받고 연속 출석을 갱신합니다.")
async def attendance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')

    if user_id not in data:
        data[user_id] = {
            'name': interaction.user.display_name,
            'balance': 0, 'last_date': '', 'streak': 0,
            'membership': '[일반] 파랭이',
            'is_admin': False,
            'avatar': str(interaction.user.display_avatar.url)
        }

    user = data[user_id]
    if user.get('last_date') == today:
        return await interaction.response.send_message("❌ 이미 오늘 출석을 완료하셨습니다.", ephemeral=True)

    user['streak'] = (user['streak'] + 1) if user.get('last_date') == yesterday else 1
    grade = user.get('membership', '[일반] 파랭이')
    multiplier = MEMBERSHIP_THEMES.get(grade, {"multiplier": 1.0})["multiplier"]

    reward = int((10000 + (user['streak'] - 1) * 5000) * multiplier)
    user['balance'] += reward
    user['last_date'] = today
    user['avatar'] = str(interaction.user.display_avatar.url)
    save_data(data)

    color = MEMBERSHIP_THEMES.get(grade, {"color": 0x5865F2})["color"]
    embed = discord.Embed(title=f"✨ {grade} 출석 완료", color=color)
    embed.add_field(name="🔥 연속 기록", value=f"{user['streak']}일차", inline=True)
    embed.add_field(name="💰 획득 금액", value=f"{reward:,}원 ({multiplier}x 적용)", inline=True)
    embed.set_footer(text=f"현재 잔액: {user['balance']:,}원")
    await interaction.response.send_message(embed=embed)

# ==========================================
# 4. 관리자 명령어 (요청하신 형식 반영)
# ==========================================
@bot.tree.command(name="어드민", description="[관리자] 유저를 어드민 리스트에 추가하거나 삭제합니다.")
@app_commands.describe(action="추가 또는 삭제 선택", member="대상 멤버 선택")
@app_commands.choices(action=[
    app_commands.Choice(name="추가", value="add"),
    app_commands.Choice(name="삭제", value="remove"),
])
async def admin_manage(interaction: discord.Interaction, action: app_commands.Choice[str], member: discord.Member):
    # 실행자가 서버 소유자이거나 이미 어드민인지 체크
    data = load_data()
    invoker_id = str(interaction.user.id)
    target_id = str(member.id)
    
    is_authorized = interaction.user.guild_permissions.administrator or data.get(invoker_id, {}).get('is_admin', False)
    if not is_authorized:
        return await interaction.response.send_message("⛔ 어드민 권한이 필요합니다.", ephemeral=True)

    if target_id not in data:
        return await interaction.response.send_message("❌ 데이터가 없는 유저입니다. 먼저 /출석체크를 진행해야 합니다.", ephemeral=True)

    if action.value == "add":
        data[target_id]['is_admin'] = True
        msg = f"✅ {member.mention} 님이 **어드민**으로 추가되었습니다."
    else:
        data[target_id]['is_admin'] = False
        msg = f"✅ {member.mention} 님의 **어드민** 권한이 회수되었습니다."

    save_data(data)
    await interaction.response.send_message(msg)

@bot.tree.command(name="멤버십설정", description="[관리자] 유저의 등급을 변경합니다.")
@app_commands.describe(member="대상 멤버", grade="변경할 등급 선택")
@app_commands.choices(grade=[
    app_commands.Choice(name="[일반] 파랭이", value="[일반] 파랭이"),
    app_commands.Choice(name="[골드] 파랭이", value="[골드] 파랭이"),
    app_commands.Choice(name="[다이아몬드] 파랭이", value="[다이아몬드] 파랭이"),
])
async def set_membership(interaction: discord.Interaction, member: discord.Member, grade: app_commands.Choice[str]):
    data = load_data()
    is_auth = data.get(str(interaction.user.id), {}).get('is_admin') or interaction.user.guild_permissions.administrator
    if not is_auth: return await interaction.response.send_message("⛔ 권한이 없습니다.", ephemeral=True)
    
    tid = str(member.id)
    if tid not in data: return await interaction.response.send_message("❌ 데이터가 없는 유저입니다.", ephemeral=True)
    
    data[tid]['membership'] = grade.value
    save_data(data)
    await interaction.response.send_message(f"✅ {member.mention} 님의 등급이 **{grade.value}**(으)로 변경되었습니다.")

# ==========================================
# 5. 웹 서버 시스템 (로그인 오류 수정 완료)
# ==========================================
@app.route('/')
def index():
    uid = session.get('user_id')
    data = load_data()
    user_info = data.get(uid) if uid else None
    
    # 등급별 탭 리스트 구성
    tab_list = {
        "일반": [u for u in data.values() if u.get('membership') == '[일반] 파랭이'],
        "골드": [u for u in data.values() if u.get('membership') == '[골드] 파랭이'],
        "다이아몬드": [u for u in data.values() if u.get('membership') == '[다이아몬드] 파랭이']
    }
    return render_template('index.html', user=user_info, tab_list=tab_list)

@app.route('/login')
def login():
    base_url = "https://discord.com/api/oauth2/authorize"
    params = {
        "client_id": CLIENT_ID, 
        "redirect_uri": REDIRECT_URI,
        "response_type": "code", 
        "scope": "identify", 
        "prompt": "consent"
    }
    # URL 파라미터를 안전하게 인코딩하여 생성
    auth_url = f"{base_url}?{'&'.join([f'{k}={requests.utils.quote(v)}' for k, v in params.items()])}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code: return redirect('/')

    token_data = {
        'client_id': CLIENT_ID, 
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code', 
        'code': code, 
        'redirect_uri': REDIRECT_URI
    }
    # 토큰 요청
    r = requests.post('https://discord.com/api/v10/oauth2/token', data=token_data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    token_res = r.json()
    
    if 'access_token' not in token_res: 
        return "로그인 실패: 토큰을 받지 못했습니다.", 400

    # 유저 정보 요청 (오타 수정: discord.com)
    u_headers = {'Authorization': f"Bearer {token_res['access_token']}"}
    u = requests.get('https://discord.com/api/v10/users/@me', headers=u_headers).json()
    uid = u['id']
    
    data = load_data()
    # 아바타 URL 처리
    avatar_url = f"https://cdn.discordapp.com/avatars/{uid}/{u['avatar']}.png" if u.get('avatar') else "https://cdn.discordapp.com/embed/avatars/0.png"

    if uid not in data:
        data[uid] = {
            'name': u.get('global_name') or u['username'],
            'balance': 0, 'streak': 0, 'last_date': '', 
            'membership': '[일반] 파랭이',
            'is_admin': False,
            'avatar': avatar_url
        }
    else:
        # 기존 유저도 아바타와 이름 갱신
        data[uid]['name'] = u.get('global_name') or u['username']
        data[uid]['avatar'] = avatar_url

    save_data(data)
    
    session.permanent = True
    session['user_id'] = uid
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def run_web():
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)
