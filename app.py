import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
import shutil
from datetime import datetime, timedelta

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG & GIAO DIỆN (UI/UX) - V36 EMERALD
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống V36 Emerald", 
    layout="wide", 
    page_icon="💎", 
    initial_sidebar_state="expanded"
)

# --- THIẾT LẬP DATABASE & FILE ---
DB_FILE = "system_v36_emerald.db"
STORAGE_DIR = "user_files"
UPLOAD_DIR = "chat_uploads"

# Tự động tạo thư mục (Viết tường minh để tránh lỗi)
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)
    
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- CSS LÀM ĐẸP (FIX LỖI CHAT DỌC & GIAO DIỆN XẤU) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #f0f2f5;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }

    /* CARD THỐNG KÊ ĐẸP */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #f0f0f0;
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 32px;
        font-weight: 700;
        color: #0ea5e9; /* Xanh ngọc hiện đại */
        margin-bottom: 8px;
    }
    .metric-label {
        font-size: 14px;
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* --- KHUNG CHAT (ĐÃ FIX LỖI BỊ BÓP MÉO) --- */
    .chat-container {
        padding: 20px;
        background: white;
        border-radius: 16px;
        height: 75vh;
        overflow-y: auto;
        border: 1px solid #e2e8f0;
        display: flex;
        flex-direction: column;
    }
    
    /* Row chứa tin nhắn */
    .msg-row {
        display: flex;
        align-items: flex-end;
        margin-bottom: 12px;
        width: 100%;
    }

    /* Tin nhắn bên PHẢI (Của tôi) */
    .msg-right {
        justify-content: flex-end;
    }
    .bubble-right {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        padding: 10px 16px;
        border-radius: 18px 18px 4px 18px;
        max-width: 70%;
        width: fit-content; /* Quan trọng: Ôm sát nội dung */
        font-size: 15px;
        line-height: 1.5;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
        word-wrap: break-word;
    }

    /* Tin nhắn bên TRÁI (Người khác) */
    .msg-left {
        justify-content: flex-start;
    }
    .bubble-left {
        background: #f1f5f9;
        color: #1e293b;
        padding: 10px 16px;
        border-radius: 18px 18px 18px 4px;
        max-width: 70%;
        width: fit-content; /* Quan trọng */
        font-size: 15px;
        line-height: 1.5;
        border: 1px solid #e2e8f0;
        word-wrap: break-word;
    }
    
    .chat-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        margin-right: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        object-fit: cover;
    }

    /* Nút bấm (Button) */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        opacity: 0.9;
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. XỬ LÝ DATABASE (AN TOÀN)
# ==============================================================================
@st.cache_resource
def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

conn = get_db_connection()
cursor = conn.cursor()

def initialize_database():
    # Bảng Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            password TEXT, 
            role TEXT, 
            qr_path TEXT, 
            zalo_name TEXT, 
            workplace_id TEXT, 
            phone TEXT, 
            license_key TEXT, 
            expiry_date TEXT
        )
    ''')
    
    # Bảng Workplaces
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workplaces (
            id TEXT PRIMARY KEY, 
            name TEXT, 
            created_by TEXT
        )
    ''')
    
    # Bảng License Keys (Dùng để kích hoạt Quản lý)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS license_keys (
            key_code TEXT PRIMARY KEY, 
            duration_days INTEGER, 
            status TEXT
        )
    ''')
    
    # Bảng Messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            workplace_id TEXT, 
            sender TEXT, 
            content TEXT, 
            timestamp TEXT, 
            msg_type TEXT
        )
    ''')
    
    # Bảng Sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, 
            username TEXT, 
            expiry TEXT
        )
    ''')
    conn.commit()

initialize_database()

SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

# ==============================================================================
# 3. CÁC HÀM HỖ TRỢ
# ==============================================================================
def load_excel_safe(file_path):
    required_columns = ["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=required_columns)
    try:
        df = pd.read_excel(file_path)
        for col in required_columns:
            if col not in df.columns:
                df[col] = ""
        return df
    except:
        return pd.DataFrame(columns=required_columns)

def save_excel_safe(dataframe, file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    dataframe.to_excel(file_path, index=False)

def get_avatar_url(name):
    # Dùng API UI Avatars tạo ảnh chữ cái đầu (đẹp & nhanh)
    return f"https://ui-avatars.com/api/?name={name}&background=0ea5e9&color=fff&size=128&bold=true"

# --- Session Management ---
def create_login_session(username):
    token = str(uuid.uuid4())
    expiry = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, expiry))
    conn.commit()
    return token

def verify_session_token(token):
    try:
        cursor.execute("SELECT username, expiry FROM sessions WHERE token=?", (token,))
        row = cursor.fetchone()
        if row:
            if datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S") > datetime.now():
                return row[0]
    except:
        pass
    return None

if "session" in st.query_params:
    token = st.query_params["session"]
    auto_user = verify_session_token(token)
    if auto_user and 'user' not in st.session_state:
        cursor.execute('SELECT * FROM users WHERE username=?', (auto_user,))
        user_data = cursor.fetchone()
        if user_data:
            st.session_state.user = user_data[0]
            st.session_state.role = user_data[2]
            st.session_state.zalo = user_data[4]
            st.session_state.wp_id = user_data[5]
            st.session_state.expiry = user_data[8]

# ==============================================================================
# 4. GIAO DIỆN CHAT (ĐÃ FIX LỖI CSS)
# ==============================================================================
@st.fragment(run_every=2)
def render_chat_window(room_id, current_user_name, chat_mode="group"):
    try:
        cursor.execute("SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,))
        messages = cursor.fetchall()[::-1]
    except:
        return

    chat_icon = "🏢" if chat_mode == "group" else "💬"
    display_name = room_id if chat_mode == "group" else "Tin nhắn riêng"
    
    st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:12px; margin-bottom:15px;'>{chat_icon} <b>{display_name}</b></div>", unsafe_allow_html=True)

    html_content = '<div class="chat-container">'
    last_sender = None
    
    for sender, content, ts, msg_type in messages:
        is_me = (sender == current_user_name)
        
        # Row wrapper
        if is_me:
            html_content += '<div class="msg-row msg-right">'
        else:
            html_content += '<div class="msg-row msg-left">'
            if sender != last_sender:
                avatar_url = get_avatar_url(sender)
                html_content += f'<img src="{avatar_url}" class="chat-avatar" title="{sender}">'
            else:
                html_content += '<div style="width:46px;"></div>'

        # Content processing
        msg_body = ""
        if msg_type == 'image':
            import base64
            if os.path.exists(content):
                with open(content, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                msg_body = f'<img src="data:image/png;base64,{img_b64}" style="max-width:250px; border-radius:12px;">'
            else:
                msg_body = "<i>⚠️ Ảnh đã bị xóa</i>"
        
        elif msg_type == 'emoji':
            msg_body = f'<div style="font-size:40px; line-height:1;">{content}</div>'
            
        elif msg_type == 'call':
            link = content.split('|')[-1]
            icon = "📹" if "video" in content else "📞"
            msg_body = f'''
            <div style="background:#e0f2fe; padding:10px; border-radius:10px; border:1px solid #bae6fd;">
                <div style="font-size:20px; margin-bottom:5px;">{icon} <b>{sender}</b> đang gọi...</div>
                <a href="{link}" target="_blank" style="background:#0284c7; color:white; padding:5px 15px; border-radius:20px; text-decoration:none; font-weight:bold; font-size:12px;">Tham gia ngay</a>
            </div>
            '''
        
        else: # Text
            # Tag highlight
            if f"@{current_user_name}" in content:
                content = f"<span style='background-color:#fef08a; padding:2px 5px; border-radius:4px; font-weight:bold;'>{content}</span>"
            msg_body = content

        # Render Bubble
        if msg_type in ['emoji', 'call']:
            html_content += f'<div>{msg_body}</div>'
        else:
            bubble_class = "bubble-right" if is_me else "bubble-left"
            name_tag = ""
            if chat_mode == "group" and not is_me and sender != last_sender:
                name_tag = f"<div style='font-size:11px; color:#64748b; margin-bottom:2px; margin-left:5px;'>{sender}</div>"
            
            html_content += f'<div>{name_tag}<div class="{bubble_class}" title="{ts}">{msg_body}</div></div>'

        html_content += '</div>' # End row
        last_sender = sender

    html_content += '</div>'
    st.markdown(html_content, unsafe_allow_html=True)
    
    # Auto Scroll
    st.markdown("""
        <script>
            var chatDiv = window.parent.document.querySelector('.chat-container');
            if (chatDiv) { chatDiv.scrollTop = chatDiv.scrollHeight; }
        </script>
    """, unsafe_allow_html=True)

# --- Dashboard Fragment ---
@st.fragment
def render_dashboard(staff_list):
    if not staff_list:
        st.warning("Chưa có dữ liệu nhân viên.")
        return

    total_debt = 0
    staff_count = len(staff_list)
    alert_count = 0
    today_str = datetime.now().strftime("%Y-%m-%d")

    for staff in staff_list:
        file_path = os.path.join(STORAGE_DIR, staff[0], "salary.xlsx")
        df = load_excel_safe(file_path)
        
        if "Trạng thái" in df.columns and "Tổng lương" in df.columns:
            debt = pd.to_numeric(df[df["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
            total_debt += debt
            
        if "Ngày" in df.columns:
            if not df[df["Ngày"].astype(str).str.contains(today_str, na=False)].empty:
                alert_count += 1

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{staff_count}</div><div class="metric-label">Nhân sự</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{total_debt:,.0f}</div><div class="metric-label">Quỹ Lương Cần Trả</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{alert_count}</div><div class="metric-label">Đang làm việc</div></div>""", unsafe_allow_html=True)
    st.write("")

# ==============================================================================
# 5. MÀN HÌNH ĐĂNG NHẬP / ĐĂNG KÝ (CÓ CHECK KEY QUẢN LÝ)
# ==============================================================================
if 'user' not in st.session_state:
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("<h1 style='text-align: center; color: #0ea5e9;'>💎 HỆ THỐNG V36 EMERALD</h1>", unsafe_allow_html=True)
        
        tab_login, tab_register, tab_super = st.tabs(["Đăng Nhập", "Đăng Ký Mới", "Super Admin"])
        
        # --- LOGIN ---
        with tab_login:
            l_user = st.text_input("Tên đăng nhập")
            l_pass = st.text_input("Mật khẩu", type="password")
            
            if st.button("Đăng nhập", type="primary", use_container_width=True):
                cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (l_user, l_pass))
                user_data = cursor.fetchone()
                
                if user_data:
                    st.session_state.user = user_data[0]
                    st.session_state.role = user_data[2]
                    st.session_state.zalo = user_data[4]
                    st.session_state.wp_id = user_data[5]
                    st.session_state.expiry = user_data[8]
                    
                    token = create_login_session(user_data[0])
                    st.query_params["session"] = token
                    st.rerun()
                else:
                    st.error("Tên đăng nhập hoặc mật khẩu không đúng.")

        # --- REGISTER (CÓ BẢO MẬT KEY) ---
        with tab_register:
            c1, c2 = st.columns(2)
            with c1:
                r_user = st.text_input("User ID (Viết liền)", key="ru")
                r_name = st.text_input("Tên hiển thị (Zalo)", key="rn")
                r_phone = st.text_input("Số điện thoại", key="rp")
            with c2:
                r_pass = st.text_input("Mật khẩu", type="password", key="rpa")
                r_role = st.radio("Đăng ký với vai trò:", ["Nhân viên", "Quản lý"], horizontal=True)
                
                r_wp = "ADMIN"
                manager_key = ""
                
                if r_role == "Nhân viên":
                    r_wp = st.text_input("Nhập Mã Chi Nhánh")
                elif r_role == "Quản lý":
                    # --- YÊU CẦU KEY KÍCH HOẠT ---
                    manager_key = st.text_input("🔑 Nhập Key Kích Hoạt (Mua từ Admin)", type="password")
            
            if st.button("Tạo Tài Khoản", use_container_width=True):
                if not r_user or not r_pass or not r_name:
                    st.warning("Vui lòng điền đầy đủ thông tin.")
                else:
                    try:
                        # 1. Kiểm tra Mã chi nhánh (nếu là NV)
                        if r_role == "Nhân viên":
                            cursor.execute("SELECT id FROM workplaces WHERE id=?", (r_wp,))
                            if not cursor.fetchone():
                                st.error("Mã Chi Nhánh không tồn tại!")
                                st.stop()
                        
                        # 2. Kiểm tra Key (nếu là Quản lý)
                        if r_role == "Quản lý":
                            cursor.execute("SELECT key_code FROM license_keys WHERE key_code=? AND status='active'", (manager_key,))
                            valid_key = cursor.fetchone()
                            if not valid_key:
                                st.error("❌ Key kích hoạt không đúng hoặc đã hết hạn! Vui lòng liên hệ Admin.")
                                st.stop()
                            else:
                                # Đánh dấu Key đã dùng
                                cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (manager_key,))
                        
                        # 3. Dọn dẹp dữ liệu cũ (Clean Data)
                        old_path = os.path.join(STORAGE_DIR, r_user)
                        if os.path.exists(old_path):
                            shutil.rmtree(old_path)
                        
                        # 4. Tạo User
                        cursor.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', 
                                       (r_user, r_pass, 'admin' if r_role=="Quản lý" else 'staff', 
                                        None, r_name, r_wp, r_phone, None, "2099-01-01"))
                        conn.commit()
                        st.success("✅ Đăng ký thành công! Bạn có thể đăng nhập ngay.")
                        
                    except sqlite3.IntegrityError:
                        st.error("Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác.")

        # --- SUPER ADMIN ---
        with tab_super:
            su_u = st.text_input("Super User")
            su_p = st.text_input("Super Password", type="password")
            if st.button("Truy Cập Gốc", use_container_width=True):
                if su_u == SUPER_ADMIN_USER and su_p == SUPER_ADMIN_PASS:
                    st.session_state.user = "SUPER_ADMIN"
                    st.session_state.role = "super_admin"
                    st.rerun()
                else:
                    st.error("Thông tin không chính xác.")
    st.stop()

# ==============================================================================
# 6. MÀN HÌNH CHÍNH
# ==============================================================================
curr_user = st.session_state.user
curr_role = st.session_state.role
curr_zalo = st.session_state.zalo if 'zalo' in st.session_state else curr_user
curr_wp = st.session_state.wp_id if 'wp_id' in st.session_state else ""

# --- SIDEBAR ---
with st.sidebar:
    st.image(get_avatar_url(curr_zalo), width=100)
    st.title(curr_zalo)
    st.caption(f"ID: {curr_user} | {curr_role}")
    
    if curr_wp and curr_wp != "ADMIN":
        st.caption(f"Chi nhánh: {curr_wp}")
    
    st.divider()
    if st.button("🚪 Đăng xuất", use_container_width=True):
        if "session" in st.query_params:
            cursor.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],))
            conn.commit()
            st.query_params.clear()
        del st.session_state.user
        st.rerun()

# --- SUPER ADMIN PANEL ---
if curr_role == 'super_admin':
    st.header("🔧 SUPER ADMIN CONSOLE")
    t1, t2 = st.tabs(["Quản Lý Key", "Dữ Liệu"])
    
    with t1:
        st.subheader("Tạo Key Kích Hoạt (Cho Quản lý đăng ký/gia hạn)")
        k_type = st.selectbox("Loại Key", ["30 Ngày", "365 Ngày", "Vĩnh viễn"])
        if st.button("Sinh Key Mới"):
            k_code = str(uuid.uuid4())[:8].upper()
            days = 36500 if k_type == "Vĩnh viễn" else (365 if k_type == "365 Ngày" else 30)
            cursor.execute("INSERT INTO license_keys VALUES (?,?,?)", (k_code, days, "active"))
            conn.commit()
            st.success(f"Key tạo thành công: {k_code}")
        
        st.write("Danh sách Key:")
        st.dataframe(pd.read_sql_query("SELECT * FROM license_keys", conn))

    with t2:
        st.error("VÙNG NGUY HIỂM")
        if st.button("💣 RESET TOÀN BỘ HỆ THỐNG (XÓA SẠCH)"):
            st.cache_resource.clear()
            cursor.close()
            conn.close()
            
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            if os.path.exists(STORAGE_DIR): shutil.rmtree(STORAGE_DIR); os.makedirs(STORAGE_DIR)
            if os.path.exists(UPLOAD_DIR): shutil.rmtree(UPLOAD_DIR); os.makedirs(UPLOAD_DIR)
            
            st.success("Đã Reset sạch sẽ. Vui lòng F5.")
            st.stop()
    st.stop()

# --- ADMIN CHECK LICENSE ---
if curr_role == 'admin':
    days_left = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if days_left < 0:
        st.error(f"🔒 Tài khoản hết hạn! (Quá hạn {-days_left} ngày)")
        key_in = st.text_input("Nhập Key gia hạn:")
        if st.button("Kích hoạt"):
            kd = cursor.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (key_in,)).fetchone()
            if kd:
                new_exp = (datetime.now() + timedelta(days=kd[0])).strftime("%Y-%m-%d")
                cursor.execute("UPDATE users SET expiry_date=? WHERE username=?", (new_exp, curr_user))
                cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (key_in,))
                conn.commit()
                st.session_state.expiry = new_exp
                st.success("Gia hạn thành công!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Key không hợp lệ.")
        st.stop()

# --- TABS CHÍNH ---
tab_chat, tab_work = st.tabs(["💬 Trung Tâm Liên Lạc", "📊 Quản Lý Công Việc"])

# === TAB 1: CHAT ===
with tab_chat:
    cmode = st.radio("", ["🏢 Nhóm Chung", "👤 Nhắn Riêng"], horizontal=True, label_visibility="collapsed")
    active_room = None
    
    if cmode == "🏢 Nhóm Chung":
        if curr_role == 'admin':
            rooms = [r[0] for r in cursor.execute("SELECT id FROM workplaces").fetchall()]
            active_room = st.selectbox("Chọn Chi nhánh:", rooms) if rooms else None
        else:
            active_room = curr_wp
    else:
        users = [u[0] for u in cursor.execute("SELECT zalo_name FROM users WHERE username != ?", (curr_user,)).fetchall()]
        if users:
            target = st.selectbox("Chọn người nhắn:", users)
            active_room = f"DM_{sorted([curr_zalo, target])[0]}_{sorted([curr_zalo, target])[1]}"

    if active_room:
        render_chat_window(active_room, curr_zalo, "group" if cmode == "🏢 Nhóm Chung" else "private")
        
        c1, c2 = st.columns([6, 1])
        with c1:
            mi = st.chat_input("Nhập tin nhắn...")
            if mi:
                cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", 
                               (active_room, curr_zalo, mi, datetime.now().strftime("%H:%M"), "text"))
                conn.commit()
        
        with c2:
            with st.popover("➕", use_container_width=True):
                if st.button("📹 Call Video", use_container_width=True):
                    lnk = f"https://meet.jit.si/v_{uuid.uuid4()}"
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                   (active_room, curr_zalo, f"v|{lnk}", datetime.now().strftime("%H:%M"), "call"))
                    conn.commit()
                    st.rerun()
                
                uimg = st.file_uploader("", type=['png','jpg'], label_visibility="collapsed")
                if uimg and st.button("Gửi Ảnh", use_container_width=True):
                    ext = uimg.name.split('.')[-1]
                    fname = f"{uuid.uuid4()}.{ext}"
                    fpath = os.path.join(UPLOAD_DIR, fname)
                    with open(fpath, "wb") as f:
                        f.write(uimg.getbuffer())
                    
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                   (active_room, curr_zalo, fpath, datetime.now().strftime("%H:%M"), "image"))
                    conn.commit()
                    st.rerun()

# === TAB 2: CÔNG VIỆC ===
with tab_work:
    if curr_role == 'admin':
        with st.expander("⚙️ CẤU HÌNH CHI NHÁNH"):
            c1, c2 = st.columns(2)
            with c1: nid = st.text_input("Mã ID Mới (VD: Q1)").upper()
            with c2: nnm = st.text_input("Tên hiển thị (VD: Cafe Quận 1)")
            if st.button("Tạo Chi Nhánh"):
                try:
                    cursor.execute("INSERT INTO workplaces VALUES (?,?,?)", (nid, nnm, curr_user))
                    conn.commit()
                    st.success("Tạo thành công!")
                    st.rerun()
                except:
                    st.error("Mã chi nhánh này đã tồn tại.")
        
        staffs = cursor.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        render_dashboard(staffs)
        
        if staffs:
            st.divider()
            s_sel = st.selectbox("📝 Quản lý nhân viên:", [f"{s[1]} ({s[0]})" for s in staffs])
            t_id = s_sel.split('(')[1].replace(')', '')
            t_file = os.path.join(STORAGE_DIR, t_id, "salary.xlsx")
            df_s = load_excel_safe(t_file)
            
            c_debt = 0
            if "Trạng thái" in df_s.columns:
                c_debt = pd.to_numeric(df_s[df_s["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
            
            c1, c2 = st.columns([2, 1])
            with c1: st.metric("Nợ lương:", f"{c_debt:,.0f} VNĐ")
            with c2:
                if c_debt > 0 and st.button("💸 Thanh Toán", use_container_width=True):
                    df_s.loc[df_s["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False), "Trạng thái"] = "nhận"
                    save_excel_safe(df_s, t_file)
                    
                    twp = [s[2] for s in staffs if s[0] == t_id][0]
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (twp, curr_zalo, f"✅ Đã thanh toán: {c_debt:,.0f}", datetime.now().strftime("%H:%M"), "text"))
                    conn.commit()
                    st.rerun()
            
            with st.expander("➕ Thêm Ca Thủ Công"):
                with st.form("adm_add"):
                    d = st.date_input("Ngày"); v = st.text_input("Vị trí", "Tại quán")
                    t1 = st.time_input("Vào"); t2 = st.time_input("Ra")
                    r = st.number_input("Lương/h (VNĐ)", value=20000, step=1000)
                    
                    if st.form_submit_button("Lưu Ca", use_container_width=True):
                        dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                        if dt2 < dt1: dt2 += timedelta(days=1)
                        h = (dt2 - dt1).total_seconds() / 3600
                        new_row = pd.DataFrame([{"Ngày": d.strftime("%Y-%m-%d"), "Vị trí": v, "Giờ vào": t1.strftime("%H:%M"), "Giờ ra": t2.strftime("%H:%M"), "Tổng lương": h*r, "Trạng thái": "chưa nhận", "Xác nhận đến": False}])
                        df_s = pd.concat([df_s, new_row], ignore_index=True)
                        save_excel_safe(df_s, t_file)
                        st.success("OK")
                        st.rerun()
            st.dataframe(df_s, use_container_width=True)

    elif curr_role == 'staff':
        my_file = os.path.join(STORAGE_DIR, curr_user, "salary.xlsx")
        df_my = load_excel_safe(my_file)
        
        my_debt = 0
        if "Trạng thái" in df_my.columns:
            my_debt = pd.to_numeric(df_my[df_my["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
        
        c1, c2 = st.columns(2)
        with c1: st.metric("💰 Quán nợ bạn:", f"{my_debt:,.0f} VNĐ")
        with c2:
            if my_debt > 0 and st.button("🔔 Đòi tiền", use_container_width=True):
                cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (curr_wp, curr_zalo, f"📣 Check lương em: {my_debt:,.0f}", datetime.now().strftime("%H:%M"), "text"))
                conn.commit()
                st.toast("Đã gửi!")
        
        with st.expander("➕ Báo cáo ca", expanded=True):
            with st.form("staff_add_shift"):
                d = st.date_input("Ngày"); v = st.text_input("Vị trí", curr_wp)
                t1 = st.time_input("Vào"); t2 = st.time_input("Ra")
                
                # CHO PHÉP NHÂN VIÊN CHỈNH LƯƠNG
                salary_rate = st.number_input("Mức lương/giờ (VNĐ)", value=20000, step=1000)
                
                if st.form_submit_button("Gửi báo cáo", use_container_width=True):
                    dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                    if dt2 < dt1: dt2 += timedelta(days=1)
                    h = (dt2 - dt1).total_seconds() / 3600
                    
                    total_pay = h * salary_rate
                    
                    new_row = pd.DataFrame([{"Ngày": d.strftime("%Y-%m-%d"), "Vị trí": v, "Giờ vào": t1.strftime("%H:%M"), "Giờ ra": t2.strftime("%H:%M"), "Tổng lương": total_pay, "Trạng thái": "chưa nhận", "Xác nhận đến": False}])
                    df_my = pd.concat([df_my, new_row], ignore_index=True)
                    save_excel_safe(df_my, my_file)
                    st.success(f"Đã lưu! (Lương: {salary_rate:,.0f} đ/h)")
                    st.rerun()
        st.dataframe(df_my, use_container_width=True)