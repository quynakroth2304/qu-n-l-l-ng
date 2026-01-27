import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import hashlib
from datetime import datetime, timedelta

# --- CẤU HÌNH ---
DB_FILE = "facebook_system.db" 
STORAGE = "user_files"
IMG_FOLDER = "chat_uploads"

if not os.path.exists(STORAGE): os.makedirs(STORAGE)
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

# --- DATABASE ---
@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def execute_db(query, params=(), fetch=False, fetch_one=False):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if fetch_one:
            result = cursor.fetchone()
            return result
        elif fetch:
            result = cursor.fetchall()
            return result
        else:
            conn.commit()
            return None
    except Exception as e:
        conn.rollback()
        return None if fetch or fetch_one else False
    finally:
        cursor.close()

def init_database():
    queries = [
        '''CREATE TABLE IF NOT EXISTS users
           (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
            qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT,
            license_key TEXT, expiry_date TEXT, avatar TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS workplaces
           (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS messages
           (id INTEGER PRIMARY KEY AUTOINCREMENT, workplace_id TEXT, 
            sender TEXT, content TEXT, timestamp TEXT, msg_type TEXT,
            avatar TEXT, reactions TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS sessions
           (token TEXT PRIMARY KEY, username TEXT, expiry TEXT)'''
    ]
    for query in queries:
        execute_db(query)

init_database()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_user_folder(uid):
    user_path = os.path.join(STORAGE, uid)
    if not os.path.exists(user_path):
        os.makedirs(user_path)
    salary_file = os.path.join(user_path, "salary.xlsx")
    if not os.path.exists(salary_file):
        df_init = pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", 
                                         "Tổng lương", "Trạng thái", "Xác nhận đến"])
        df_init.to_excel(salary_file, index=False)
    return salary_file

def load_excel_safe(path):
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", 
                                      "Tổng lương", "Trạng thái", "Xác nhận đến"])
    try:
        return pd.read_excel(path, engine='openpyxl')
    except:
        return pd.DataFrame()

def find_col(df, keywords):
    if isinstance(keywords, str): keywords = [keywords]
    for col in df.columns:
        for key in keywords:
            if key.lower() in str(col).lower(): return col
    return None

SUPER_ADMIN_USER = "admin"
SUPER_ADMIN_PASS = hash_password("123")

# === CSS GIỐNG FACEBOOK ===
def load_facebook_css():
    st.markdown("""
    <style>
        /* RESET & BASE */
        .main {
            background: #18191a !important;
        }
        
        .stApp {
            background: #18191a;
        }
        
        /* SIDEBAR GIỐNG FACEBOOK */
        [data-testid="stSidebar"] {
            background: #242526 !important;
            border-right: 1px solid #3a3b3c;
        }
        
        [data-testid="stSidebar"] .stMarkdown {
            color: #e4e6eb;
        }
        
        /* HEADER PROFILE */
        .profile-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        
        .profile-name {
            font-size: 24px;
            font-weight: 600;
            color: white;
            margin: 0;
        }
        
        .profile-role {
            color: rgba(255,255,255,0.8);
            font-size: 14px;
        }
        
        /* CHAT CONTAINER - GIỐNG MESSENGER */
        .chat-container {
            background: #242526;
            border-radius: 16px;
            padding: 16px;
            margin: 10px 0;
            box-shadow: 0 1px 2px rgba(0,0,0,0.2);
        }
        
        /* MESSAGE BUBBLE */
        .message-bubble {
            display: flex;
            align-items: flex-start;
            margin: 12px 0;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message-bubble.me {
            flex-direction: row-reverse;
        }
        
        .message-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 14px;
            margin: 0 8px;
            flex-shrink: 0;
        }
        
        .message-content {
            max-width: 60%;
        }
        
        .message-bubble.me .message-content {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }
        
        .message-sender {
            font-size: 13px;
            font-weight: 600;
            color: #b0b3b8;
            margin-bottom: 4px;
        }
        
        .message-text {
            background: #3a3b3c;
            color: #e4e6eb;
            padding: 10px 16px;
            border-radius: 18px;
            font-size: 15px;
            line-height: 1.4;
            word-wrap: break-word;
        }
        
        .message-bubble.me .message-text {
            background: linear-gradient(135deg, #0084ff, #0066cc);
            color: white;
        }
        
        .message-time {
            font-size: 11px;
            color: #8a8d91;
            margin-top: 4px;
            padding: 0 8px;
        }
        
        .message-tagged {
            background: linear-gradient(135deg, #ff6b6b, #ee5a6f) !important;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(255,107,107,0.4); }
            50% { box-shadow: 0 0 0 10px rgba(255,107,107,0); }
        }
        
        /* IMAGE MESSAGE */
        .message-image {
            max-width: 250px;
            border-radius: 12px;
            margin-top: 4px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .message-image:hover {
            transform: scale(1.05);
        }
        
        /* EMOJI REACTION */
        .message-emoji {
            font-size: 48px;
            animation: bounce 0.5s;
        }
        
        @keyframes bounce {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.2); }
        }
        
        /* INPUT BOX - GIỐNG FACEBOOK */
        .stTextInput input, .stTextArea textarea {
            background: #3a3b3c !important;
            border: none !important;
            color: #e4e6eb !important;
            border-radius: 20px !important;
            padding: 12px 16px !important;
            font-size: 15px !important;
        }
        
        .stTextInput input:focus, .stTextArea textarea:focus {
            box-shadow: 0 0 0 2px #0084ff !important;
        }
        
        /* BUTTONS */
        .stButton button {
            background: linear-gradient(135deg, #0084ff, #0066cc) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
            transition: all 0.3s !important;
        }
        
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,132,255,0.4) !important;
        }
        
        /* CARD STYLE */
        .work-card {
            background: #242526;
            border-radius: 12px;
            padding: 20px;
            margin: 16px 0;
            border: 1px solid #3a3b3c;
            transition: all 0.3s;
        }
        
        .work-card:hover {
            border-color: #0084ff;
            box-shadow: 0 4px 16px rgba(0,132,255,0.2);
        }
        
        /* METRICS */
        [data-testid="stMetricValue"] {
            color: #0084ff !important;
            font-size: 32px !important;
            font-weight: 700 !important;
        }
        
        [data-testid="stMetricLabel"] {
            color: #b0b3b8 !important;
        }
        
        /* DATAFRAME */
        .stDataFrame {
            background: #242526;
            border-radius: 12px;
            overflow: hidden;
        }
        
        /* EXPANDER */
        .streamlit-expanderHeader {
            background: #3a3b3c !important;
            color: #e4e6eb !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }
        
        /* TABS */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: #242526;
            padding: 8px;
            border-radius: 12px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            color: #b0b3b8;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 600;
        }
        
        .stTabs [aria-selected="true"] {
            background: #0084ff !important;
            color: white !important;
        }
        
        /* SELECTBOX */
        .stSelectbox > div > div {
            background: #3a3b3c !important;
            color: #e4e6eb !important;
            border-radius: 8px !important;
        }
        
        /* CHAT INPUT */
        .stChatInput textarea {
            background: #3a3b3c !important;
            color: #e4e6eb !important;
            border: none !important;
            border-radius: 24px !important;
        }
        
        /* POPOVER */
        [data-baseweb="popover"] {
            background: #242526 !important;
            border: 1px solid #3a3b3c !important;
            border-radius: 12px !important;
        }
        
        /* SCROLLBAR */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #242526;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #3a3b3c;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #4a4b4c;
        }
        
        /* NOTIFICATION BADGE */
        .notification-badge {
            background: #e74c3c;
            color: white;
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 8px;
        }
        
        /* ONLINE STATUS */
        .online-dot {
            width: 12px;
            height: 12px;
            background: #31a24c;
            border-radius: 50%;
            border: 2px solid #242526;
            position: absolute;
            bottom: 0;
            right: 0;
        }
    </style>
    """, unsafe_allow_html=True)

st.set_page_config(
    page_title="Workplace Chat",
    layout="wide",
    page_icon="💬",
    initial_sidebar_state="expanded"
)

load_facebook_css()

# SESSION
def create_session(username):
    token = str(uuid.uuid4())
    exp = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    execute_db("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, exp))
    return token

def get_user_from_session(token):
    row = execute_db("SELECT username, expiry FROM sessions WHERE token=?", (token,), fetch_one=True)
    if row:
        expiry = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
        if expiry > datetime.now():
            return row[0]
        else:
            execute_db("DELETE FROM sessions WHERE token=?", (token,))
    return None

if "session" in st.query_params:
    auto_user = get_user_from_session(st.query_params["session"])
    if auto_user and 'user' not in st.session_state:
        ud = execute_db('SELECT * FROM users WHERE username=?', (auto_user,), fetch_one=True)
        if ud:
            st.session_state.user = ud[0]
            st.session_state.role = ud[2]
            st.session_state.zalo = ud[4]
            st.session_state.wp_id = ud[5]

# === CHAT FRAGMENT ===
@st.fragment(run_every=2)
def render_facebook_chat(room_id, current_user_zalo):
    count = execute_db("SELECT COUNT(*) FROM messages WHERE workplace_id=?", 
                       (room_id,), fetch_one=True)
    msg_count = count[0] if count else 0
    
    cache_key = f"chat_{room_id}"
    if (cache_key not in st.session_state or 
        st.session_state.get(f"{cache_key}_count", 0) != msg_count):
        
        msgs = execute_db(
            "SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50",
            (room_id,), fetch=True
        )
        st.session_state[cache_key] = msgs[::-1] if msgs else []
        st.session_state[f"{cache_key}_count"] = msg_count
    
    msgs = st.session_state.get(cache_key, [])
    
    with st.container(height=500):
        if not msgs:
            st.markdown("""
                <div style='text-align: center; padding: 60px 20px; color: #8a8d91;'>
                    <div style='font-size: 48px; margin-bottom: 16px;'>💬</div>
                    <div style='font-size: 16px;'>Chưa có tin nhắn nào</div>
                    <div style='font-size: 14px; margin-top: 8px;'>Hãy bắt đầu cuộc trò chuyện!</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            for sender, content, ts, m_type in msgs:
                is_me = (sender == current_user_zalo)
                is_tagged = (m_type == 'text' and content and f"@{current_user_zalo}" in content)
                
                avatar_letter = sender[0].upper() if sender else "?"
                bubble_class = "me" if is_me else ""
                
                if m_type == 'emoji':
                    st.markdown(f"""
                        <div class="message-bubble {bubble_class}">
                            <div class="message-avatar">{avatar_letter}</div>
                            <div class="message-content">
                                <div class="message-sender">{sender}</div>
                                <div class="message-emoji">{content}</div>
                                <div class="message-time">{ts}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                elif m_type == 'image':
                    if os.path.exists(content):
                        st.markdown(f"""
                            <div class="message-bubble {bubble_class}">
                                <div class="message-avatar">{avatar_letter}</div>
                                <div class="message-content">
                                    <div class="message-sender">{sender}</div>
                        """, unsafe_allow_html=True)
                        st.image(content, width=250)
                        st.markdown(f"""
                                    <div class="message-time">{ts}</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    text_class = "message-tagged" if is_tagged else "message-text"
                    st.markdown(f"""
                        <div class="message-bubble {bubble_class}">
                            <div class="message-avatar">{avatar_letter}</div>
                            <div class="message-content">
                                <div class="message-sender">{sender}</div>
                                <div class="{text_class}">{content}</div>
                                <div class="message-time">{ts}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

# === LOGIN PAGE ===
if 'user' not in st.session_state:
    st.markdown("""
        <div style='text-align: center; padding: 40px 0;'>
            <h1 style='font-size: 48px; background: linear-gradient(135deg, #667eea, #764ba2); 
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                       font-weight: 800; margin-bottom: 8px;'>
                Workplace
            </h1>
            <p style='color: #8a8d91; font-size: 18px;'>Kết nối và làm việc cùng nhau</p>
        </div>
    """, unsafe_allow_html=True)
    
    t_log, t_reg = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])
    
    with t_log:
        with st.form("login_form"):
            st.markdown("<h3 style='color: #e4e6eb; margin-bottom: 20px;'>Đăng nhập</h3>", unsafe_allow_html=True)
            u_l = st.text_input("👤 User ID", key="l_u")
            p_l = st.text_input("🔒 Mật khẩu", type="password", key="l_p")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                submitted = st.form_submit_button("Đăng nhập", use_container_width=True)
            
            if submitted:
                ud = execute_db(
                    'SELECT * FROM users WHERE username=? AND password=?',
                    (u_l, hash_password(p_l)), fetch_one=True
                )
                
                if ud:
                    st.session_state.user = ud[0]
                    st.session_state.role = ud[2]
                    st.session_state.zalo = ud[4]
                    st.session_state.wp_id = ud[5]
                    token = create_session(ud[0])
                    st.query_params["session"] = token
                    st.success(f"✅ Chào {ud[4]}!")
                    st.rerun()
                else:
                    st.error("❌ Sai thông tin đăng nhập!")
    
    with t_reg:
        with st.form("register_form"):
            st.markdown("<h3 style='color: #e4e6eb; margin-bottom: 20px;'>Tạo tài khoản mới</h3>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                u_r = st.text_input("👤 User ID", key="r_u")
                z_r = st.text_input("🏷️ Tên hiển thị", key="r_z")
            with col2:
                p_r = st.text_input("📱 Số điện thoại", key="r_p")
                pass_r = st.text_input("🔒 Mật khẩu", type="password", key="r_pa")
            
            r_r = st.radio("Vai trò", ["Nhân viên", "Quản lý"], horizontal=True)
            wp_in = st.text_input("🏢 Mã chi nhánh", key="r_w") if r_r == "Nhân viên" else "ADMIN"
            
            submitted = st.form_submit_button("Đăng ký", use_container_width=True)
            
            if submitted:
                if len(u_r) < 3:
                    st.error("❌ User ID phải >= 3 ký tự!")
                elif len(pass_r) < 4:
                    st.error("❌ Mật khẩu phải >= 4 ký tự!")
                elif not z_r.strip():
                    st.error("❌ Vui lòng nhập tên hiển thị!")
                else:
                    if r_r == "Nhân viên":
                        wp_exists = execute_db("SELECT id FROM workplaces WHERE id=?", (wp_in,), fetch_one=True)
                        if not wp_exists:
                            st.error(f"❌ Chi nhánh '{wp_in}' không tồn tại!")
                            st.stop()
                    
                    result = execute_db(
                        'INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?)',
                        (u_r, hash_password(pass_r), 'admin' if r_r=="Quản lý" else 'staff', 
                         None, z_r, wp_in, p_r, None, "2099-01-01", None)
                    )
                    
                    if result is not False:
                        ensure_user_folder(u_r)
                        st.success(f"✅ Tạo tài khoản thành công!")
                    else:
                        st.error("❌ User ID đã tồn tại!")
    
    st.stop()

# === MAIN APP ===
user = st.session_state.user
role = st.session_state.role
zalo = st.session_state.get('zalo', user)
wp_id = st.session_state.get('wp_id', "")

# SIDEBAR
with st.sidebar:
    st.markdown(f"""
        <div class="profile-header">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 50px; height: 50px; background: white; border-radius: 50%; 
                            display: flex; align-items: center; justify-content: center; 
                            font-size: 24px; font-weight: 700; color: #667eea;">
                    {zalo[0].upper()}
                </div>
                <div>
                    <div class="profile-name">{zalo}</div>
                    <div class="profile-role">{'🔧 Quản lý' if role == 'admin' else '👤 Nhân viên'}</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"<div style='color: #b0b3b8; font-size: 14px; margin: 16px 0;'>🏢 Chi nhánh: <strong style='color: #e4e6eb;'>{wp_id}</strong></div>", unsafe_allow_html=True)
    
    if st.button("🚪 Đăng xuất", use_container_width=True):
        if "session" in st.query_params:
            execute_db("DELETE FROM sessions WHERE token=?", (st.query_params["session"],))
            st.query_params.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# MAIN TABS
tab_chat, tab_work = st.tabs(["💬 Tin nhắn", "📊 Công việc"])

# === TAB CHAT ===
with tab_chat:
    st.markdown("<h2 style='color: #e4e6eb; margin-bottom: 20px;'>💬 Tin nhắn</h2>", unsafe_allow_html=True)
    
    active_room = wp_id
    
    if role == 'admin':
        rooms_data = execute_db("SELECT id, name FROM workplaces", fetch=True)
        rooms = [(r[0], r[1]) for r in rooms_data] if rooms_data else []
        
        if not rooms:
            st.warning("⚠️ Chưa có chi nhánh! Tạo ở tab 'Công việc'")
        else:
            room_options = [f"{r[1]} ({r[0]})" for r in rooms]
            selected = st.selectbox("🏢 Chọn phòng chat", room_options, key="room_sel")
            active_room = selected.split("(")[1].replace(")", "")
    
    if active_room:
        render_facebook_chat(active_room, zalo)
        
        # INPUT
        col1, col2 = st.columns([6, 1])
        
        with col1:
            if prompt := st.chat_input("Aa"):
                ts = datetime.now().strftime("%H:%M")
                execute_db(
                    "INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)",
                    (active_room, zalo, prompt, ts, "text")
                )
                cache_key = f"chat_{active_room}"
                if cache_key in st.session_state:
                    del st.session_state[cache_key]
                st.rerun()
        
        with col2:
            with st.popover("➕", use_container_width=True):
                st.markdown("<div style='color: #e4e6eb; font-weight: 600; margin-bottom: 12px;'>Gửi nội dung</div>", unsafe_allow_html=True)
                
                if st.button("👍 Like", use_container_width=True): 
                    execute_db(
                        "INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)",
                        (active_room, zalo, "👍", datetime.now().strftime("%H:%M"), "emoji")
                    )
                    st.rerun()
                
                if st.button("❤️ Love", use_container_width=True):
                    execute_db(
                        "INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)",
                        (active_room, zalo, "❤️", datetime.now().strftime("%H:%M"), "emoji")
                    )
                    st.rerun()
                
                st.divider()
                
                img = st.file_uploader("📷 Gửi ảnh", type=['png','jpg','jpeg'], key="img_up")
                if img and st.button("✅ Gửi", use_container_width=True):
                    ext = img.name.split('.')[-1]
                    fname = f"{uuid.uuid4()}.{ext}"
                    fpath = os.path.join(IMG_FOLDER, fname)
                    
                    with open(fpath, "wb") as f:
                        f.write(img.getbuffer())
                    
                    execute_db(
                        "INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)",
                        (active_room, zalo, fpath, datetime.now().strftime("%H:%M"), "image")
                    )
                    st.rerun()

# === TAB WORK ===
with tab_work:
    if role == 'admin':
        st.markdown("<h2 style='color: #e4e6eb; margin-bottom: 20px;'>📊 Quản lý công việc</h2>", unsafe_allow_html=True)
        
        with st.expander("🏢 Tạo chi nhánh mới", expanded=False):
            with st.form("create_workplace"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    new_id = st.text_input("Mã ID").upper().strip()
                    new_name = st.text_input("Tên chi nhánh").strip()
                with col2:
                    st.write("")
                    st.write("")
                    if st.form_submit_button("➕ Tạo", use_container_width=True):
                        if not new_id or not new_name:
                            st.error("❌ Điền đầy đủ thông tin!")
                        else:
                            result = execute_db("INSERT INTO workplaces VALUES (?,?,?)", (new_id, new_name, user))
                            if result is not False:
                                st.success(f"✅ Tạo: {new_name}")
                                st.rerun()
                            else:
                                st.error("❌ Mã đã tồn tại!")
        
        st.divider()
        
        # STAFF MANAGEMENT
        staffs = execute_db("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'", fetch=True)
        
        if not staffs:
            st.info("📭 Chưa có nhân viên")
        else:
            total_debt = 0
            for s in staffs:
                p_path = ensure_user_folder(s[0])
                df = load_excel_safe(p_path)
                c_tt = find_col(df, ["trạng thái", "nhận"])
                c_tl = find_col(df, ["tổng", "lương"])
                if c_tt and c_tl and not df.empty:
                    debt_rows = df[df[c_tt].astype(str).str.lower().str.contains('chưa', na=False)]
                    total_debt += pd.to_numeric(debt_rows[c_tl], errors='coerce').sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("👥 Tổng nhân viên", len(staffs))
            with col2:
                st.metric("💰 Tổng nợ lương", f"{total_debt:,.0f} đ")
            with col3:
                st.metric("🏢 Chi nhánh", len(set([s[2] for s in staffs])))
            
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            
            s_sel = st.selectbox("Chọn nhân viên", [f"{s[1]} ({s[0]}) - {s[2]}" for s in staffs])
            uid = s_sel.split("(")[1].split(")")[0]
            
            p_path = ensure_user_folder(uid)
            df_t = load_excel_safe(p_path)
            
            c_tt = find_col(df_t, ["trạng thái", "nhận"])
            c_tl = find_col(df_t, ["tổng", "lương"])
            debt = 0
            
            if c_tt and c_tl and not df_t.empty:
                debt_rows = df_t[df_t[c_tt].astype(str).str.lower().str.contains('chưa', na=False)]
                debt = pd.to_numeric(debt_rows[c_tl], errors='coerce').sum()
            
            st.markdown(f"""
                <div class="work-card">
                    <h3 style='color: #e4e6eb; margin-bottom: 16px;'>{s_sel.split('(')[0].strip()}</h3>
                    <div style='display: flex; gap: 20px; align-items: center;'>
                        <div>
                            <div style='color: #8a8d91; font-size: 14px;'>Nợ lương</div>
                            <div style='color: #0084ff; font-size: 28px; font-weight: 700;'>{debt:,.0f} đ</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if debt > 0:
                if st.button("💵 Thanh toán toàn bộ", type="primary"):
                    df_t.loc[df_t[c_tt].astype(str).str.lower().str.contains('chưa', na=False), c_tt] = "Đã nhận"
                    df_t.to_excel(p_path, index=False)
                    staff_wp = [s[2] for s in staffs if s[0] == uid][0]
                    execute_db(
                        "INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)",
                        (staff_wp, zalo, f"✅ Đã trả lương: {debt:,.0f} VNĐ", 
                         datetime.now().strftime("%H:%M"), "text")
                    )
                    st.success(f"✅ Đã thanh toán!")
                    st.rerun()
            
            with st.expander("➕ Thêm ca làm việc"):
                with st.form("add_shift"):
                    col1, col2 = st.columns(2)
                    with col1:
                        d = st.date_input("📅 Ngày")
                        v = st.text_input("📍 Vị trí", value=[s[2] for s in staffs if s[0] == uid][0])
                    with col2:
                        t1 = st.time_input("🕐 Vào")
                        t2 = st.time_input("🕐 Ra")
                    
                    luong_gio = st.number_input("💵 Lương/giờ (đ)", value=20000, step=5000)
                    
                    start = datetime.combine(d, t1)
                    end = datetime.combine(d, t2)
                    if end < start:
                        end += timedelta(days=1)
                    hours = (end - start).total_seconds() / 3600
                    total_salary = hours * luong_gio
                    
                    st.info(f"⏱️ {hours:.2f}h → {total_salary:,.0f} đ")
                    
                    if st.form_submit_button("✅ Lưu ca", use_container_width=True):
                        new_row = {
                            find_col(df_t, "ngày"): str(d),
                            find_col(df_t, "vị trí"): v,
                            find_col(df_t, "vào"): str(t1),
                            find_col(df_t, "ra"): str(t2),
                            find_col(df_t, "tổng"): total_salary,
                            "Trạng thái": "Chưa nhận",
                            "Xác nhận đến": False
                        }
                        df_t = pd.concat([df_t, pd.DataFrame([new_row])], ignore_index=True)
                        df_t.to_excel(p_path, index=False)
                        st.success(f"✅ Đã thêm ca!")
                        st.rerun()
            
            st.dataframe(df_t, use_container_width=True, height=400)
    
    elif role == 'staff':
        st.markdown("<h2 style='color: #e4e6eb; margin-bottom: 20px;'>💼 Ví của tôi</h2>", unsafe_allow_html=True)
        
        p_path = ensure_user_folder(user)
        df = load_excel_safe(p_path)
        
        c_tt = find_col(df, ["trạng thái", "nhận"])
        c_tl = find_col(df, ["tổng", "lương"])
        total_due = 0
        
        if c_tt and c_tl and not df.empty:
            debt_rows = df[df[c_tt].astype(str).str.lower().str.contains('chưa', na=False)]
            total_due = pd.to_numeric(debt_rows[c_tl], errors='coerce').sum()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.metric("💰 Đang nợ bạn", f"{total_due:,.0f} đ")
        with col2:
            if total_due > 0:
                if st.button("📣 Nhắc quản lý", type="primary"):
                    execute_db(
                        "INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)",
                        (wp_id, zalo, f"📣 Anh/chị ơi, trả lương em: {total_due:,.0f} đ", 
                         datetime.now().strftime("%H:%M"), "text")
                    )
                    st.toast("✅ Đã gửi!")
        
        with st.expander("➕ Thêm ca làm"):
            with st.form("staff_add"):
                col1, col2 = st.columns(2)
                with col1:
                    d = st.date_input("📅 Ngày")
                    v = st.text_input("📍 Vị trí", value=wp_id)
                with col2:
                    t1 = st.time_input("🕐 Vào")
                    t2 = st.time_input("🕐 Ra")
                
                luong_gio = st.number_input("💵 Lương/giờ (đ)", value=20000, step=5000)
                
                start = datetime.combine(d, t1)
                end = datetime.combine(d, t2)
                if end < start:
                    end += timedelta(days=1)
                hours = (end - start).total_seconds() / 3600
                total_salary = hours * luong_gio
                
                st.info(f"⏱️ {hours:.2f}h → {total_salary:,.0f} đ")
                
                if st.form_submit_button("✅ Lưu", use_container_width=True):
                    new_row = {
                        find_col(df, "ngày"): str(d),
                        find_col(df, "vị trí"): v,
                        find_col(df, "vào"): str(t1),
                        find_col(df, "ra"): str(t2),
                        find_col(df, "tổng"): total_salary,
                        "Trạng thái": "Chưa nhận",
                        "Xác nhận đến": False
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_excel(p_path, index=False)
                    st.success("✅ OK!")
                    st.rerun()
        
        st.dataframe(df, use_container_width=True, height=400)
