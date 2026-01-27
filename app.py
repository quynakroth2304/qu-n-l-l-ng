import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
import shutil
from datetime import datetime, timedelta

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG V42 (FINAL LOGIC & UI FIX)
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống V42 Final", 
    layout="wide", 
    page_icon="💎", 
    initial_sidebar_state="expanded"
)

# --- THIẾT LẬP DATABASE ---
DB_FILE = "system_v42_final.db"
STORAGE_DIR = "user_files"
UPLOAD_DIR = "chat_uploads"

if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- CSS FIX LỖI VỠ KHUNG CHAT (TRIỆT ĐỂ) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

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

    /* CARD THỐNG KÊ */
    .metric-card {
        background: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #f0f0f0;
        text-align: center; margin-bottom: 10px;
    }
    .metric-value { font-size: 28px; font-weight: 700; color: #0ea5e9; margin-bottom: 5px; }
    .metric-label { font-size: 13px; color: #64748b; font-weight: 600; text-transform: uppercase; }

    /* --- KHUNG CHAT (ĐÃ SỬA LỖI GÃY CHỮ) --- */
    .chat-container {
        padding: 20px;
        background: white;
        border-radius: 16px;
        height: 78vh;
        overflow-y: auto;
        border: 1px solid #e2e8f0;
        display: flex;
        flex-direction: column;
    }
    
    .msg-row {
        display: flex;
        align-items: flex-end;
        margin-bottom: 10px;
        width: 100%;
    }

    /* Tin nhắn Phải (Tôi) */
    .msg-right {
        justify-content: flex-end;
    }
    .bubble-right {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        padding: 10px 16px;
        border-radius: 18px 18px 4px 18px;
        
        /* FIX: Dùng inline-block để tự động co giãn */
        display: inline-block;
        max-width: 80%;
        min-width: 20px; /* Tránh bị bóp quá nhỏ */
        
        text-align: left;
        word-wrap: break-word; /* Chỉ xuống dòng khi cần thiết */
        white-space: pre-wrap; /* Giữ format xuống dòng */
        
        font-size: 15px;
        line-height: 1.5;
        box-shadow: 0 2px 5px rgba(37, 99, 235, 0.2);
    }

    /* Tin nhắn Trái (Người khác) */
    .msg-left {
        justify-content: flex-start;
    }
    .bubble-left {
        background: #f1f5f9;
        color: #1e293b;
        padding: 10px 16px;
        border-radius: 18px 18px 18px 4px;
        
        display: inline-block;
        max-width: 80%;
        min-width: 20px;
        
        text-align: left;
        word-wrap: break-word;
        white-space: pre-wrap;
        
        font-size: 15px;
        line-height: 1.5;
        border: 1px solid #e2e8f0;
    }
    
    .chat-avatar {
        width: 32px; height: 32px; border-radius: 50%;
        margin-right: 8px; flex-shrink: 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); object-fit: cover;
    }

    /* Nút bấm */
    .stButton > button {
        border-radius: 8px; font-weight: 600; border: none; padding: 0.5rem 1rem;
        transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton > button:hover { opacity: 0.9; transform: translateY(-1px); }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. DATABASE & LOGIC
# ==============================================================================
@st.cache_resource
def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

conn = get_db_connection()
cursor = conn.cursor()

def initialize_database():
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT, license_key TEXT, expiry_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS workplaces (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS license_keys (key_code TEXT PRIMARY KEY, duration_days INTEGER, status TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, workplace_id TEXT, sender TEXT, content TEXT, timestamp TEXT, msg_type TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT, expiry TEXT)''')
    conn.commit()

initialize_database()

SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

# --- Utils Excel ---
def load_excel_safe(file_path):
    required_columns = ["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=required_columns)
    try:
        df = pd.read_excel(file_path)
        for col in required_columns:
            if col not in df.columns:
                df[col] = ""
        # Chuẩn hóa cột Trạng thái để tránh lỗi so sánh
        df["Trạng thái"] = df["Trạng thái"].fillna("chưa nhận").astype(str)
        df["Xác nhận đến"] = df["Xác nhận đến"].fillna(False)
        return df
    except:
        return pd.DataFrame(columns=required_columns)

def save_excel_safe(dataframe, file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    dataframe.to_excel(file_path, index=False)

def get_avatar_url(name):
    return f"https://ui-avatars.com/api/?name={name}&background=0ea5e9&color=fff&size=128&bold=true"

# --- Session ---
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
        if row and datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S") > datetime.now():
            return row[0]
    except: pass
    return None

if "session" in st.query_params:
    token = st.query_params["session"]
    auto_user = verify_session_token(token)
    if auto_user and 'user' not in st.session_state:
        cursor.execute('SELECT * FROM users WHERE username=?', (auto_user,))
        user_data = cursor.fetchone()
        if user_data:
            st.session_state.user=user_data[0]; st.session_state.role=user_data[2]; st.session_state.zalo=user_data[4]; st.session_state.wp_id=user_data[5]; st.session_state.expiry=user_data[8]

# ==============================================================================
# 3. GIAO DIỆN CHAT (RENDER)
# ==============================================================================
@st.fragment(run_every=2)
def render_chat_window(room_id, current_user_name, chat_mode="group"):
    try:
        cursor.execute("SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,))
        messages = cursor.fetchall()[::-1]
    except: return

    chat_icon = "🏢" if chat_mode == "group" else "💬"
    display_name = room_id if chat_mode == "group" else "Tin nhắn riêng"
    st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:12px; margin-bottom:15px;'>{chat_icon} <b>{display_name}</b></div>", unsafe_allow_html=True)

    html_content = '<div class="chat-container">'
    last_sender = None
    
    for sender, content, ts, msg_type in messages:
        is_me = (sender == current_user_name)
        
        if is_me:
            html_content += '<div class="msg-row msg-right">'
        else:
            html_content += '<div class="msg-row msg-left">'
            if sender != last_sender:
                html_content += f'<img src="{get_avatar_url(sender)}" class="chat-avatar" title="{sender}">'
            else:
                html_content += '<div style="width:40px;"></div>'

        msg_body = ""
        if msg_type == 'image':
            import base64
            if os.path.exists(content):
                with open(content, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                msg_body = f'<img src="data:image/png;base64,{img_b64}" style="max-width:250px; border-radius:12px;">'
            else:
                msg_body = "<i>⚠️ Ảnh đã xóa</i>"
        elif msg_type == 'emoji':
            msg_body = f'<div style="font-size:40px; line-height:1;">{content}</div>'
        elif msg_type == 'call':
            link = content.split('|')[-1]; icon = "📹" if "video" in content else "📞"
            msg_body = f'<div style="background:#e0f2fe; padding:10px; border-radius:10px; border:1px solid #bae6fd;"><div style="font-size:18px; margin-bottom:5px;">{icon} <b>{sender}</b> đang gọi...</div><a href="{link}" target="_blank" style="background:#0284c7; color:white; padding:5px 15px; border-radius:20px; text-decoration:none; font-weight:bold; font-size:12px;">Tham gia ngay</a></div>'
        else: # Text
            if f"@{current_user_name}" in content:
                content = f"<span style='background-color:#fef08a; padding:2px 5px; border-radius:4px; font-weight:bold;'>{content}</span>"
            msg_body = content

        if msg_type in ['emoji', 'call']:
            html_content += f'<div>{msg_body}</div>'
        else:
            bubble_class = "bubble-right" if is_me else "bubble-left"
            name_tag = ""
            if chat_mode == "group" and not is_me and sender != last_sender:
                name_tag = f"<div style='font-size:11px; color:#64748b; margin-bottom:2px; margin-left:5px;'>{sender}</div>"
            html_content += f'<div>{name_tag}<div class="{bubble_class}" title="{ts}">{msg_body}</div></div>'

        html_content += '</div>'
        last_sender = sender

    html_content += '</div>'
    st.markdown(html_content, unsafe_allow_html=True)
    st.markdown("<script>var c=window.parent.document.querySelector('.chat-container');if(c){c.scrollTop=c.scrollHeight;}</script>", unsafe_allow_html=True)

# --- Dashboard ---
@st.fragment
def render_dashboard(staff_list):
    if not staff_list: st.warning("Chưa có nhân viên."); return
    debt = 0; count = len(staff_list); pending = 0
    
    for staff in staff_list:
        file_path = os.path.join(STORAGE_DIR, staff[0], "salary.xlsx")
        df = load_excel_safe(file_path)
        
        # Tính nợ: Lấy tất cả trạng thái KHÔNG PHẢI "đã nhận"
        if "Trạng thái" in df.columns and "Tổng lương" in df.columns:
            unpaid = df[~df["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)]
            debt += pd.to_numeric(unpaid["Tổng lương"], errors='coerce').sum()
            
        if "Xác nhận đến" in df.columns:
            pending += len(df[df["Xác nhận đến"].astype(str).str.lower() == "false"])

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"""<div class="metric-card"><div class="metric-value">{count}</div><div class="metric-label">Nhân sự</div></div>""", unsafe_allow_html=True)
    with c2: st.markdown(f"""<div class="metric-card"><div class="metric-value">{debt:,.0f}</div><div class="metric-label">Tổng Quỹ Lương</div></div>""", unsafe_allow_html=True)
    with c3:
        color = "#ef4444" if pending > 0 else "#22c55e"
        st.markdown(f"""<div class="metric-card"><div class="metric-value" style="color:{color}">{pending}</div><div class="metric-label">Ca chưa xác nhận</div></div>""", unsafe_allow_html=True)
    st.write("")

# ==============================================================================
# 4. ĐĂNG NHẬP / ĐĂNG KÝ
# ==============================================================================
if 'user' not in st.session_state:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #0ea5e9;'>💎 HỆ THỐNG V42</h1>", unsafe_allow_html=True)
        tab_login, tab_register, tab_super = st.tabs(["Đăng Nhập", "Đăng Ký Mới", "Super Admin"])
        
        with tab_login:
            l_user = st.text_input("Tên đăng nhập")
            l_pass = st.text_input("Mật khẩu", type="password")
            if st.button("Đăng nhập", type="primary", use_container_width=True):
                cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (l_user, l_pass))
                user_data = cursor.fetchone()
                if user_data:
                    st.session_state.user=user_data[0]; st.session_state.role=user_data[2]; st.session_state.zalo=user_data[4]; st.session_state.wp_id=user_data[5]; st.session_state.expiry=user_data[8]
                    token = create_login_session(user_data[0]); st.query_params["session"] = token; st.rerun()
                else: st.error("Thông tin sai.")

        with tab_register:
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                r_user = st.text_input("User ID (Viết liền)", key="ru")
                r_name = st.text_input("Tên hiển thị", key="rn")
                r_phone = st.text_input("SĐT", key="rp")
            with c_r2:
                r_pass = st.text_input("Mật khẩu", type="password", key="rpa")
                r_role = st.radio("Vai trò:", ["Nhân viên", "Quản lý"], horizontal=True)
                r_wp = "ADMIN"; manager_key = ""
                if r_role == "Nhân viên": r_wp = st.text_input("Mã Chi Nhánh")
                elif r_role == "Quản lý": manager_key = st.text_input("🔑 Nhập Key Admin", type="password")
            
            if st.button("Tạo Tài Khoản", use_container_width=True):
                if not r_user or not r_pass: st.warning("Điền đủ thông tin!")
                else:
                    try:
                        if r_role == "Nhân viên":
                            cursor.execute("SELECT id FROM workplaces WHERE id=?", (r_wp,))
                            if not cursor.fetchone(): st.error("Mã Chi Nhánh không tồn tại!"); st.stop()
                        if r_role == "Quản lý":
                            cursor.execute("SELECT key_code FROM license_keys WHERE key_code=? AND status='active'", (manager_key,))
                            if not cursor.fetchone(): st.error("Key sai hoặc hết hạn!"); st.stop()
                            else: cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (manager_key,))
                        
                        op = os.path.join(STORAGE_DIR, r_user)
                        if os.path.exists(op): shutil.rmtree(op)
                        cursor.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (r_user, r_pass, 'admin' if r_role=="Quản lý" else 'staff', None, r_name, r_wp, r_phone, None, "2099-01-01"))
                        conn.commit(); st.success("✅ Thành công!"); 
                    except sqlite3.IntegrityError: st.error("Tên đăng nhập trùng.")

        with tab_super:
            su_u = st.text_input("Super User"); su_p = st.text_input("Super Pass", type="password")
            if st.button("Truy Cập Gốc", use_container_width=True):
                if su_u == SUPER_ADMIN_USER and su_p == SUPER_ADMIN_PASS:
                    st.session_state.user="SUPER_ADMIN"; st.session_state.role="super_admin"; st.rerun()
                else: st.error("Sai thông tin.")
    st.stop()

# ==============================================================================
# 5. MÀN HÌNH CHÍNH
# ==============================================================================
curr_user = st.session_state.user; curr_role = st.session_state.role; curr_zalo = st.session_state.zalo; curr_wp = st.session_state.wp_id

with st.sidebar:
    st.image(get_avatar_url(curr_zalo), width=100); st.title(curr_zalo); st.caption(f"ID: {curr_user} | {curr_role}")
    if curr_wp and curr_wp != "ADMIN": st.caption(f"Chi nhánh: {curr_wp}")
    st.divider()
    if st.button("🚪 Đăng xuất", use_container_width=True):
        if "session" in st.query_params: cursor.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],)); conn.commit(); st.query_params.clear()
        del st.session_state.user; st.rerun()

if curr_role == 'super_admin':
    st.header("🔧 SUPER ADMIN")
    t1, t2 = st.tabs(["Key", "Reset"])
    with t1:
        kt = st.selectbox("Loại Key", ["30 Ngày", "365 Ngày", "Vĩnh viễn"])
        if st.button("Sinh Key"): 
            k = str(uuid.uuid4())[:8].upper(); d = 36500 if kt == "Vĩnh viễn" else (365 if kt == "365 Ngày" else 30)
            cursor.execute("INSERT INTO license_keys VALUES (?,?,?)", (k, d, "active")); conn.commit(); st.success(f"Key: {k}")
        st.dataframe(pd.read_sql_query("SELECT * FROM license_keys", conn))
    with t2:
        if st.button("💣 RESET TOÀN BỘ"): 
            st.cache_resource.clear(); cursor.close(); conn.close()
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            if os.path.exists(STORAGE_DIR): shutil.rmtree(STORAGE_DIR); os.makedirs(STORAGE_DIR)
            if os.path.exists(UPLOAD_DIR): shutil.rmtree(UPLOAD_DIR); os.makedirs(UPLOAD_DIR)
            st.success("Đã Reset!"); st.stop()
    st.stop()

if curr_role == 'admin':
    dl = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if dl < 0:
        st.error(f"🔒 Hết hạn!"); k = st.text_input("Nhập Key:")
        if st.button("Kích hoạt"):
            kd = cursor.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (k,)).fetchone()
            if kd:
                n = (datetime.now() + timedelta(days=kd[0])).strftime("%Y-%m-%d")
                cursor.execute("UPDATE users SET expiry_date=? WHERE username=?", (n, curr_user)); cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (k,)); conn.commit(); st.session_state.expiry=n; st.success("OK!"); time.sleep(1); st.rerun()
            else: st.error("Key lỗi.")
        st.stop()

tab_chat, tab_work = st.tabs(["💬 Trung Tâm Liên Lạc", "📊 Quản Lý & Công Việc"])

with tab_chat:
    cmode = st.radio("", ["🏢 Nhóm Chung", "👤 Nhắn Riêng"], horizontal=True, label_visibility="collapsed")
    active_room = None
    if cmode == "🏢 Nhóm Chung":
        if curr_role == 'admin':
            rooms = [r[0] for r in cursor.execute("SELECT id FROM workplaces").fetchall()]
            active_room = st.selectbox("Chọn Chi nhánh:", rooms) if rooms else None
        else: active_room = curr_wp
    else:
        users = [u[0] for u in cursor.execute("SELECT zalo_name FROM users WHERE username != ?", (curr_user,)).fetchall()]
        if users: target = st.selectbox("Chọn người nhắn:", users); active_room = f"DM_{sorted([curr_zalo, target])[0]}_{sorted([curr_zalo, target])[1]}"

    if active_room:
        render_chat_window(active_room, curr_zalo, "group" if cmode == "🏢 Nhóm Chung" else "private")
        c1, c2 = st.columns([6, 1])
        with c1:
            mi = st.chat_input("Nhập tin nhắn...")
            if mi: cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", (active_room, curr_zalo, mi, datetime.now().strftime("%H:%M"), "text")); conn.commit()
        with c2:
            with st.popover("➕", use_container_width=True):
                if st.button("📹 Call Video", use_container_width=True):
                    lnk = f"https://meet.jit.si/v_{uuid.uuid4()}"; cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (active_room, curr_zalo, f"v|{lnk}", datetime.now().strftime("%H:%M"), "call")); conn.commit(); st.rerun()
                uimg = st.file_uploader("", type=['png','jpg'], label_visibility="collapsed")
                if uimg and st.button("Gửi Ảnh", use_container_width=True):
                    ext = uimg.name.split('.')[-1]; fname = f"{uuid.uuid4()}.{ext}"; fpath = os.path.join(UPLOAD_DIR, fname)
                    with open(fpath, "wb") as f: f.write(uimg.getbuffer())
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (active_room, curr_zalo, fpath, datetime.now().strftime("%H:%M"), "image")); conn.commit(); st.rerun()

with tab_work:
    # --- GIAO DIỆN QUẢN LÝ ---
    if curr_role == 'admin':
        # [NEW] QUẢN LÝ CHI NHÁNH
        with st.expander("🏢 QUẢN LÝ CHI NHÁNH"):
            tab_create, tab_list = st.tabs(["Tạo Mới", "Danh Sách"])
            with tab_create:
                c1, c2 = st.columns(2)
                with c1: nid = st.text_input("Mã Chi Nhánh (VD: Q1)").upper()
                with c2: nnm = st.text_input("Tên Hiển Thị (VD: Cafe Quận 1)")
                if st.button("Tạo Chi Nhánh Mới"):
                    try: cursor.execute("INSERT INTO workplaces VALUES (?,?,?)", (nid, nnm, curr_user)); conn.commit(); st.success("Thành công!"); st.rerun()
                    except: st.error("Mã này đã tồn tại.")
            with tab_list:
                my_branches = pd.read_sql_query(f"SELECT * FROM workplaces WHERE created_by='{curr_user}'", conn)
                st.dataframe(my_branches)

        staff_list = cursor.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        render_dashboard(staff_list)
        
        if staff_list:
            st.divider()
            s_sel = st.selectbox("📝 Chọn nhân viên:", [f"{s[1]} ({s[0]})" for s in staff_list])
            t_id = s_sel.split('(')[1].replace(')', '')
            t_file = os.path.join(STORAGE_DIR, t_id, "salary.xlsx")
            df_s = load_excel_safe(t_file)
            
            pending_count = len(df_s[df_s["Xác nhận đến"].astype(str).str.lower() == "false"])
            c_debt = pd.to_numeric(df_s[~df_s["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)]["Tổng lương"], errors='coerce').sum()
            
            st.info(f"Thông tin liên hệ: {staff_list[[s[0] for s in staff_list].index(t_id)][3]}")
            
            c_a1, c_a2, c_a3 = st.columns(3)
            with c_a1: st.metric("Nợ lương:", f"{c_debt:,.0f} VNĐ")
            with c_a2: st.metric("Ca chưa duyệt:", f"{pending_count}")
            with c_a3:
                if pending_count > 0:
                    if st.button("✅ DUYỆT CHẤM CÔNG", use_container_width=True):
                        df_s.loc[df_s["Xác nhận đến"].astype(str).str.lower() == "false", "Xác nhận đến"] = True
                        save_excel_safe(df_s, t_file); st.success("Đã duyệt!"); time.sleep(1); st.rerun()
                
                if c_debt > 0:
                    # [NEW] QUY TRÌNH THANH TOÁN 2 BƯỚC
                    if st.button("💸 BÁO ĐÃ CHUYỂN KHOẢN", use_container_width=True):
                        # Chuyển trạng thái sang "Chờ xác nhận"
                        mask = ~df_s["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)
                        df_s.loc[mask, "Trạng thái"] = "chờ xác nhận"
                        save_excel_safe(df_s, t_file)
                        
                        # Gửi tin nhắn thông báo
                        twp = [s[2] for s in staff_list if s[0] == t_id][0]
                        cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (twp, curr_zalo, f"🔔 Đã chuyển khoản lương: {c_debt:,.0f}. Vui lòng xác nhận!", datetime.now().strftime("%H:%M"), "text"))
                        conn.commit()
                        st.success("Đã báo nhân viên!"); st.rerun()
            
            with st.expander("➕ Thêm Ca Làm Việc"):
                with st.form("adm_add"):
                    d = st.date_input("Ngày"); v = st.text_input("Vị trí", "Tại quán")
                    t1 = st.time_input("Vào"); t2 = st.time_input("Ra"); r = st.number_input("Lương/h", 20000)
                    if st.form_submit_button("Lưu"):
                        dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                        if dt2 < dt1: dt2 += timedelta(days=1)
                        h = (dt2 - dt1).total_seconds() / 3600
                        new_row = pd.DataFrame([{"Ngày": d.strftime("%Y-%m-%d"), "Vị trí": v, "Giờ vào": t1.strftime("%H:%M"), "Giờ ra": t2.strftime("%H:%M"), "Tổng lương": h * r, "Trạng thái": "chưa nhận", "Xác nhận đến": True}])
                        df_s = pd.concat([df_s, new_row], ignore_index=True); save_excel_safe(df_s, t_file); st.success("OK"); st.rerun()
            st.dataframe(df_s, use_container_width=True)

    # --- GIAO DIỆN NHÂN VIÊN ---
    elif curr_role == 'staff':
        my_file = os.path.join(STORAGE_DIR, curr_user, "salary.xlsx")
        df_my = load_excel_safe(my_file)
        
        # Tính nợ: Các dòng chưa "đã nhận"
        mask_debt = ~df_my["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)
        my_debt = pd.to_numeric(df_my[mask_debt]["Tổng lương"], errors='coerce').sum()
        
        # Check xem có khoản nào "chờ xác nhận" không
        waiting_confirm = len(df_my[df_my["Trạng thái"].astype(str).str.lower() == "chờ xác nhận"]) > 0
        
        c1, c2 = st.columns(2)
        with c1: st.metric("💰 Quán nợ bạn:", f"{my_debt:,.0f} VNĐ")
        with c2:
            if waiting_confirm:
                st.info("Quản lý báo đã chuyển khoản!")
                if st.button("✅ XÁC NHẬN ĐÃ NHẬN TIỀN", use_container_width=True):
                    # Cập nhật thành "đã nhận"
                    df_my.loc[df_my["Trạng thái"].astype(str).str.lower() == "chờ xác nhận", "Trạng thái"] = "đã nhận"
                    save_excel_safe(df_my, my_file)
                    # Báo lại quản lý
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (curr_wp, curr_zalo, "✅ Em đã nhận được tiền lương ạ!", datetime.now().strftime("%H:%M"), "text"))
                    conn.commit()
                    st.success("Đã xác nhận!"); st.rerun()
            elif my_debt > 0:
                if st.button("🔔 Nhắc Quản lý", use_container_width=True):
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (curr_wp, curr_zalo, f"📣 Check lương giúp em: {my_debt:,.0f}", datetime.now().strftime("%H:%M"), "text"))
                    conn.commit(); st.toast("Đã gửi!")
        
        with st.expander("➕ Báo cáo ca", expanded=True):
            with st.form("staff_add"):
                d = st.date_input("Ngày"); v = st.text_input("Vị trí", curr_wp); t1 = st.time_input("Vào"); t2 = st.time_input("Ra"); sr = st.number_input("Lương/h", 20000)
                if st.form_submit_button("Gửi báo cáo"):
                    dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                    if dt2 < dt1: dt2 += timedelta(days=1)
                    h = (dt2 - dt1).total_seconds() / 3600
                    new = pd.DataFrame([{"Ngày": d.strftime("%Y-%m-%d"), "Vị trí": v, "Giờ vào": t1.strftime("%H:%M"), "Giờ ra": t2.strftime("%H:%M"), "Tổng lương": h * sr, "Trạng thái": "chưa nhận", "Xác nhận đến": False}])
                    df_my = pd.concat([df_my, new], ignore_index=True); save_excel_safe(df_my, my_file); st.success("Đã lưu!"); st.rerun()
        st.dataframe(df_my, use_container_width=True)