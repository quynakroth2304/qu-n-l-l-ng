import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
import shutil
from datetime import datetime, timedelta

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG & GIAO DIỆN (UI/UX)
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống Quản Lý V35 (Enterprise)", 
    layout="wide", 
    page_icon="🏢", 
    initial_sidebar_state="expanded"
)

# --- THIẾT LẬP FILE HỆ THỐNG ---
DB_FILE = "system_v35_enterprise.db"
STORAGE_DIR = "user_files"
UPLOAD_DIR = "chat_uploads"

# Tự động tạo thư mục nếu chưa có (Viết tường minh để tránh lỗi)
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)
    
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- CSS LÀM ĐẸP (Giao diện Messenger chuẩn & Thoáng) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
        background-color: #f0f2f5;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #ddd;
    }

    /* Card Thống kê */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        text-align: center;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #1877f2;
        margin-bottom: 5px;
    }
    .metric-label {
        font-size: 14px;
        color: #65676b;
        text-transform: uppercase;
        font-weight: 500;
    }

    /* Khung Chat Cao & Thoáng */
    .chat-container {
        padding: 20px;
        background: white;
        border-radius: 15px;
        height: 78vh; /* Chiều cao lớn */
        overflow-y: auto;
        border: 1px solid #ddd;
        box-shadow: inset 0 0 15px rgba(0,0,0,0.03);
    }
    
    /* Tin nhắn Phải (Tôi) */
    .msg-right {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 15px;
        align-items: flex-end;
    }
    .bubble-right {
        background: linear-gradient(to right, #0084ff, #0099ff);
        color: white;
        padding: 12px 18px;
        border-radius: 20px 20px 4px 20px;
        max-width: 75%;
        font-size: 15px;
        box-shadow: 0 3px 8px rgba(0,132,255,0.2);
    }

    /* Tin nhắn Trái (Người khác) */
    .msg-left {
        display: flex;
        justify-content: flex-start;
        margin-bottom: 15px;
        align-items: flex-end;
    }
    .bubble-left {
        background: #e4e6eb;
        color: #050505;
        padding: 12px 18px;
        border-radius: 20px 20px 20px 4px;
        max-width: 75%;
        font-size: 15px;
    }
    
    .chat-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        margin-right: 12px;
        border: 1px solid #eee;
    }

    /* Call & Button */
    .call-card {
        background: #e8f5e9;
        border: 1px solid #c8e6c9;
        border-radius: 12px;
        padding: 15px;
        display: flex;
        align-items: center;
        gap: 15px;
        width: fit-content;
    }
    .call-btn {
        background-color: #2e7d32;
        color: white !important;
        text-decoration: none;
        padding: 10px 22px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
        border: none;
        display: inline-block;
    }
    
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: 0.2s;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. XỬ LÝ DATABASE (AN TOÀN & TƯỜNG MINH)
# ==============================================================================
@st.cache_resource
def get_db_connection():
    # Kết nối DB với chế độ check_same_thread=False để tránh lỗi luồng
    return sqlite3.connect(DB_FILE, check_same_thread=False)

conn = get_db_connection()
cursor = conn.cursor()

def initialize_database():
    # Tạo các bảng dữ liệu nếu chưa tồn tại
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workplaces (
            id TEXT PRIMARY KEY, 
            name TEXT, 
            created_by TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS license_keys (
            key_code TEXT PRIMARY KEY, 
            duration_days INTEGER, 
            status TEXT
        )
    ''')
    
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, 
            username TEXT, 
            expiry TEXT
        )
    ''')
    conn.commit()

# Khởi tạo DB ngay lập tức
initialize_database()

SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

# ==============================================================================
# 3. CÁC HÀM HỖ TRỢ (UTILS)
# ==============================================================================

def load_excel_safe(file_path):
    """
    Đọc file Excel an toàn. Nếu file lỗi hoặc thiếu cột sẽ tự bù vào.
    """
    required_columns = ["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]
    
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=required_columns)
    
    try:
        df = pd.read_excel(file_path)
        # Kiểm tra từng cột, nếu thiếu thì thêm vào
        for col in required_columns:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        # Nếu lỗi đọc file, trả về bảng rỗng để không crash app
        return pd.DataFrame(columns=required_columns)

def save_excel_safe(dataframe, file_path):
    """
    Lưu file Excel an toàn. Tự động tạo thư mục nếu chưa có.
    """
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        dataframe.to_excel(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"Lỗi khi lưu file: {e}")
        return False

def get_avatar_url(name):
    """Lấy avatar từ dịch vụ DiceBear"""
    return f"https://api.dicebear.com/7.x/notionists/svg?seed={name}&backgroundColor=b6e3f4"

# --- Quản lý Session ---
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
            expiry_str = row[1]
            if datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S") > datetime.now():
                return row[0]
    except:
        pass
    return None

# Kiểm tra session đầu chương trình
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
# 4. GIAO DIỆN CHAT (RENDER LOGIC)
# ==============================================================================
@st.fragment(run_every=2)
def render_chat_window(room_id, current_user_name, chat_mode="group"):
    try:
        # Lấy 50 tin nhắn mới nhất
        cursor.execute("SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,))
        messages = cursor.fetchall()[::-1] # Đảo ngược để tin mới ở dưới
    except:
        return

    chat_icon = "🏢" if chat_mode == "group" else "💬"
    display_name = room_id if chat_mode == "group" else "Cuộc hội thoại riêng"
    
    st.markdown(f"<div style='text-align:center; color:#888; font-size:12px; margin-bottom:10px;'>{chat_icon} <b>{display_name}</b></div>", unsafe_allow_html=True)

    html_content = '<div class="chat-container">'
    last_sender = None
    
    for sender, content, ts, msg_type in messages:
        is_me = (sender == current_user_name)
        
        # Mở thẻ div bao ngoài (Hàng tin nhắn)
        if is_me:
            html_content += '<div class="msg-right">'
        else:
            html_content += '<div class="msg-left">'
            # Avatar logic
            if sender != last_sender:
                avatar_url = get_avatar_url(sender)
                html_content += f'<img src="{avatar_url}" class="chat-avatar" title="{sender}">'
            else:
                html_content += '<div style="width:52px;"></div>' # Spacer

        # Xử lý nội dung tin nhắn
        msg_body = ""
        
        if msg_type == 'image':
            import base64
            if os.path.exists(content):
                with open(content, "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode()
                msg_body = f'<img src="data:image/png;base64,{img_base64}" style="max-width:250px; border-radius:12px;">'
            else:
                msg_body = "<i>⚠️ Hình ảnh không tồn tại</i>"
        
        elif msg_type == 'emoji':
            msg_body = f'<div style="font-size:48px; line-height:1;">{content}</div>'
            
        elif msg_type == 'call':
            link = content.split('|')[-1]
            icon = "📹" if "video" in content else "📞"
            text_call = "Video Call" if "video" in content else "Voice Call"
            
            msg_body = f'''
            <div class="call-card">
                <div style="font-size:28px;">{icon}</div>
                <div>
                    <div style="font-weight:bold; font-size:14px; color:#2e7d32;">{sender} đang gọi...</div>
                    <div style="margin-top:8px;">
                        <a href="{link}" target="_blank" class="call-btn">Tham gia {text_call}</a>
                    </div>
                </div>
            </div>
            '''
        
        else: # Tin nhắn văn bản
            if f"@{current_user_name}" in content:
                content = f"<span style='background-color:#fff3cd; padding:2px 5px; border-radius:4px; font-weight:bold;'>{content}</span>"
            msg_body = content

        # Đóng gói vào Bubble
        if msg_type in ['emoji', 'call']:
            html_content += f'<div>{msg_body}</div>'
        else:
            bubble_class = "bubble-right" if is_me else "bubble-left"
            name_label = ""
            if chat_mode == "group" and not is_me and sender != last_sender:
                name_label = f"<div style='font-size:11px; color:#888; margin-bottom:4px; margin-left:5px;'>{sender}</div>"
            
            html_content += f'<div>{name_label}<div class="{bubble_class}" title="{ts}">{msg_body}</div></div>'

        html_content += '</div>' # Đóng thẻ Hàng
        last_sender = sender

    html_content += '</div>' # Đóng Container
    
    st.markdown(html_content, unsafe_allow_html=True)
    
    # Javascript tự cuộn
    st.markdown("""
        <script>
            var chatDiv = window.parent.document.querySelector('.chat-container');
            if (chatDiv) {
                chatDiv.scrollTop = chatDiv.scrollHeight;
            }
        </script>
    """, unsafe_allow_html=True)

# --- Dashboard (Fragment) ---
@st.fragment
def render_dashboard(staff_list):
    if not staff_list:
        st.warning("Chưa có nhân viên nào.")
        return

    total_debt = 0
    staff_count = len(staff_list)
    alert_count = 0
    today_str = datetime.now().strftime("%Y-%m-%d")

    for staff in staff_list:
        staff_id = staff[0]
        file_path = os.path.join(STORAGE_DIR, staff_id, "salary.xlsx")
        df = load_excel_safe(file_path)
        
        # Tính nợ
        if "Trạng thái" in df.columns and "Tổng lương" in df.columns:
            debt = pd.to_numeric(df[df["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
            total_debt += debt
            
        # Đếm ca làm
        if "Ngày" in df.columns:
            if not df[df["Ngày"].astype(str).str.contains(today_str, na=False)].empty:
                alert_count += 1

    # Hiển thị Card
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{staff_count}</div><div class="metric-label">Nhân sự</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{total_debt:,.0f}</div><div class="metric-label">Quỹ Lương Nợ (VNĐ)</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{alert_count}</div><div class="metric-label">Ca làm hôm nay</div></div>""", unsafe_allow_html=True)
    
    st.write("") # Khoảng cách

# ==============================================================================
# 5. ĐĂNG NHẬP / ĐĂNG KÝ
# ==============================================================================
if 'user' not in st.session_state:
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("<h1 style='text-align: center; color: #1877f2;'>🌐 HỆ THỐNG V35</h1>", unsafe_allow_html=True)
        
        tab_login, tab_register, tab_super = st.tabs(["Đăng Nhập", "Đăng Ký Mới", "Super Admin"])
        
        # --- TAB ĐĂNG NHẬP ---
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
                    st.error("Sai thông tin đăng nhập!")

        # --- TAB ĐĂNG KÝ (CÓ CLEAN DATA CŨ) ---
        with tab_register:
            c1, c2 = st.columns(2)
            with c1:
                r_user = st.text_input("User ID (Viết liền, không dấu)", key="ru")
                r_name = st.text_input("Tên hiển thị (Zalo)", key="rn")
                r_phone = st.text_input("Số điện thoại", key="rp")
            with c2:
                r_pass = st.text_input("Mật khẩu", type="password", key="rpa")
                r_role = st.radio("Vai trò", ["Nhân viên", "Quản lý"], horizontal=True)
                
                r_wp = "ADMIN"
                if r_role == "Nhân viên":
                    r_wp = st.text_input("Mã Chi Nhánh")
            
            if st.button("Tạo Tài Khoản", use_container_width=True):
                if not r_user or not r_pass:
                    st.warning("Vui lòng điền đủ thông tin!")
                else:
                    try:
                        if r_role == "Nhân viên":
                            cursor.execute("SELECT id FROM workplaces WHERE id=?", (r_wp,))
                            if not cursor.fetchone():
                                st.error("Mã Chi Nhánh không tồn tại!")
                                st.stop()
                        
                        # XÓA FILE CŨ NẾU CÓ (Để tránh hiện ca cũ của nick cũ)
                        old_path = os.path.join(STORAGE_DIR, r_user)
                        if os.path.exists(old_path):
                            shutil.rmtree(old_path)
                        
                        cursor.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', 
                                       (r_user, r_pass, 'admin' if r_role=="Quản lý" else 'staff', 
                                        None, r_name, r_wp, r_phone, None, "2099-01-01"))
                        conn.commit()
                        st.success("✅ Đăng ký thành công! Dữ liệu mới hoàn toàn.")
                    except sqlite3.IntegrityError:
                        st.error("Tên đăng nhập đã tồn tại.")

        # --- TAB SUPER ADMIN ---
        with tab_super:
            su_u = st.text_input("Super User")
            su_p = st.text_input("Super Password", type="password")
            if st.button("Truy Cập Gốc", use_container_width=True):
                if su_u == SUPER_ADMIN_USER and su_p == SUPER_ADMIN_PASS:
                    st.session_state.user = "SUPER_ADMIN"
                    st.session_state.role = "super_admin"
                    st.rerun()
                else:
                    st.error("Sai thông tin!")
    st.stop()

# ==============================================================================
# 6. MÀN HÌNH CHÍNH (SAU KHI ĐĂNG NHẬP)
# ==============================================================================
curr_user = st.session_state.user
curr_role = st.session_state.role
curr_zalo = st.session_state.zalo if 'zalo' in st.session_state else curr_user
curr_wp = st.session_state.wp_id if 'wp_id' in st.session_state else ""

# --- SIDEBAR ---
with st.sidebar:
    st.image(get_avatar_url(curr_zalo), width=100)
    st.title(curr_zalo)
    st.caption(f"ID: {curr_user} | Role: {curr_role}")
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
    st.header("🔧 QUẢN TRỊ HỆ THỐNG")
    t1, t2 = st.tabs(["Quản Lý Key", "Reset Hệ Thống"])
    
    with t1:
        kt = st.selectbox("Loại Key", ["30 Ngày", "365 Ngày", "Vĩnh viễn"])
        if st.button("Sinh Key Mới"):
            kc = str(uuid.uuid4())[:8].upper()
            days = 36500 if kt == "Vĩnh viễn" else (365 if kt == "365 Ngày" else 30)
            cursor.execute("INSERT INTO license_keys VALUES (?,?,?)", (kc, days, "active"))
            conn.commit()
            st.success(f"Key: {kc}")
        
        st.dataframe(pd.read_sql_query("SELECT * FROM license_keys", conn))

    with t2:
        st.error("⚠️ CẢNH BÁO: Hành động này xóa sạch 100% dữ liệu (Database + File Excel + Ảnh)!")
        if st.button("💣 XÓA SẠCH TẬN GỐC (HARD RESET)"):
            st.cache_resource.clear()
            cursor.close()
            conn.close()
            
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            
            if os.path.exists(STORAGE_DIR):
                shutil.rmtree(STORAGE_DIR)
                os.makedirs(STORAGE_DIR)
                
            if os.path.exists(UPLOAD_DIR):
                shutil.rmtree(UPLOAD_DIR)
                os.makedirs(UPLOAD_DIR)
                
            st.success("Đã Reset sạch sẽ! Vui lòng F5 lại trang.")
            st.stop()
    st.stop()

# --- CHECK LICENSE (ADMIN) ---
if curr_role == 'admin':
    days_left = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if days_left < 0:
        st.error(f"🔒 Tài khoản hết hạn! (Quá hạn {-days_left} ngày)")
        key_in = st.text_input("Nhập License Key:")
        if st.button("Kích hoạt"):
            kd = cursor.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (key_in,)).fetchone()
            if kd:
                new_exp = (datetime.now() + timedelta(days=kd[0])).strftime("%Y-%m-%d")
                cursor.execute("UPDATE users SET expiry_date=? WHERE username=?", (new_exp, curr_user))
                cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (key_in,))
                conn.commit()
                st.session_state.expiry = new_exp
                st.success("Thành công! Vui lòng đợi...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Key lỗi.")
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
            with c1: nid = st.text_input("Mã ID Mới").upper()
            with c2: nnm = st.text_input("Tên hiển thị")
            if st.button("Tạo Chi Nhánh"):
                try:
                    cursor.execute("INSERT INTO workplaces VALUES (?,?,?)", (nid, nnm, curr_user))
                    conn.commit()
                    st.success("OK")
                    st.rerun()
                except: st.error("Trùng mã")
        
        staffs = cursor.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        render_dashboard(staffs)
        
        if staffs:
            st.divider()
            s_sel = st.selectbox("📝 Quản lý:", [f"{s[1]} ({s[0]})" for s in staffs])
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
                with st.form("admin_add"):
                    d = st.date_input("Ngày")
                    v = st.text_input("Vị trí", "Tại quán")
                    t1 = st.time_input("Vào")
                    t2 = st.time_input("Ra")
                    r = st.number_input("Lương/h (VNĐ)", value=20000, step=1000)
                    
                    if st.form_submit_button("Lưu Ca", use_container_width=True):
                        dt1 = datetime.combine(d, t1)
                        dt2 = datetime.combine(d, t2)
                        if dt2 < dt1: dt2 += timedelta(days=1)
                        
                        h = (dt2 - dt1).total_seconds() / 3600
                        
                        new_row = pd.DataFrame([{
                            "Ngày": d.strftime("%Y-%m-%d"), 
                            "Vị trí": v, 
                            "Giờ vào": t1.strftime("%H:%M"), 
                            "Giờ ra": t2.strftime("%H:%M"), 
                            "Tổng lương": h * r, 
                            "Trạng thái": "chưa nhận", 
                            "Xác nhận đến": False
                        }])
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
                d = st.date_input("Ngày")
                v = st.text_input("Vị trí", curr_wp)
                t1 = st.time_input("Vào")
                t2 = st.time_input("Ra")
                
                # --- TÍNH NĂNG MỚI: NHẬP MỨC LƯƠNG ---
                salary_rate = st.number_input("Mức lương/giờ (VNĐ)", value=20000, step=1000, help="Nhập mức lương thỏa thuận")
                
                if st.form_submit_button("Gửi báo cáo", use_container_width=True):
                    dt1 = datetime.combine(d, t1)
                    dt2 = datetime.combine(d, t2)
                    if dt2 < dt1: dt2 += timedelta(days=1)
                    
                    h = (dt2 - dt1).total_seconds() / 3600
                    
                    # Tính tổng lương dựa trên mức lương nhập vào
                    total_pay = h * salary_rate
                    
                    new_row = pd.DataFrame([{
                        "Ngày": d.strftime("%Y-%m-%d"), 
                        "Vị trí": v, 
                        "Giờ vào": t1.strftime("%H:%M"), 
                        "Giờ ra": t2.strftime("%H:%M"), 
                        "Tổng lương": total_pay, 
                        "Trạng thái": "chưa nhận", 
                        "Xác nhận đến": False
                    }])
                    df_my = pd.concat([df_my, new_row], ignore_index=True)
                    save_excel_safe(df_my, my_file)
                    st.success(f"Đã lưu! (Mức lương: {salary_rate:,.0f} đ/h)")
                    st.rerun()
        st.dataframe(df_my, use_container_width=True)