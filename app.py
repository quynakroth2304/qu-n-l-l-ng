import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
import shutil
from datetime import datetime, timedelta

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG V44 (INTERACTIVE CHAT)
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống V44 Interactive", 
    layout="wide", 
    page_icon="💸", 
    initial_sidebar_state="expanded"
)

# --- THIẾT LẬP DATABASE & THƯ MỤC ---
DATABASE_FILE = "system_v44_interactive.db"
STORAGE_DIRECTORY = "user_files"
UPLOAD_DIRECTORY = "chat_uploads"

if not os.path.exists(STORAGE_DIRECTORY):
    os.makedirs(STORAGE_DIRECTORY)
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

# --- CSS GIAO DIỆN (CÓ THÊM STYLE CHO THẺ THANH TOÁN) ---
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
        background: white; border-radius: 12px; padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #f0f0f0;
        text-align: center; margin-bottom: 10px;
    }
    .metric-value { font-size: 28px; font-weight: 700; color: #0ea5e9; margin-bottom: 5px; }
    .metric-label { font-size: 13px; color: #64748b; font-weight: 600; text-transform: uppercase; }

    /* KHUNG CHAT */
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
    
    .message-row {
        display: flex;
        align-items: flex-end;
        margin-bottom: 12px;
        width: 100%;
    }

    .message-right { justify-content: flex-end; }
    .bubble-right {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white; padding: 10px 16px; border-radius: 18px 18px 4px 18px;
        display: inline-block; max-width: 80%; min-width: 20px;
        text-align: left; word-wrap: break-word; white-space: pre-wrap;
        font-size: 15px; line-height: 1.5;
        box-shadow: 0 2px 5px rgba(37, 99, 235, 0.2);
    }

    .message-left { justify-content: flex-start; }
    .bubble-left {
        background: #f1f5f9; color: #1e293b; padding: 10px 16px;
        border-radius: 18px 18px 18px 4px;
        display: inline-block; max-width: 80%; min-width: 20px;
        text-align: left; word-wrap: break-word; white-space: pre-wrap;
        font-size: 15px; line-height: 1.5; border: 1px solid #e2e8f0;
    }
    
    .chat-avatar {
        width: 36px; height: 36px; border-radius: 50%;
        margin-right: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex-shrink: 0;
    }

    /* PAYMENT CARD TRONG CHAT */
    .payment-bubble {
        background: #ecfdf5; /* Xanh lá nhạt */
        border: 1px solid #10b981;
        color: #064e3b;
        padding: 15px;
        border-radius: 12px;
        min-width: 250px;
    }
    .payment-header { font-weight: bold; font-size: 14px; display: flex; align-items: center; gap: 5px; }
    .payment-amount { font-size: 24px; font-weight: 800; color: #059669; margin: 5px 0; }
    
    /* Nút bấm */
    .stButton > button {
        border-radius: 8px; font-weight: 600; border: none; padding: 0.5rem 1rem;
        transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton > button:hover { opacity: 0.9; transform: translateY(-1px); }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. XỬ LÝ DATABASE
# ==============================================================================
@st.cache_resource
def get_database_connection():
    return sqlite3.connect(DATABASE_FILE, check_same_thread=False)

connection = get_database_connection()
cursor = connection.cursor()

def initialize_database_tables():
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT, license_key TEXT, expiry_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS workplaces (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS license_keys (key_code TEXT PRIMARY KEY, duration_days INTEGER, status TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, workplace_id TEXT, sender TEXT, content TEXT, timestamp TEXT, msg_type TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT, expiry TEXT)''')
    connection.commit()

initialize_database_tables()

SUPER_ADMIN_USERNAME = "admin_vip"
SUPER_ADMIN_PASSWORD = "vip888"

# ==============================================================================
# 3. UTILS (Load/Save Excel)
# ==============================================================================
def load_excel_safe(file_path):
    required_columns = ["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]
    if not os.path.exists(file_path): return pd.DataFrame(columns=required_columns)
    try:
        data_frame = pd.read_excel(file_path)
        for column in required_columns:
            if column not in data_frame.columns: data_frame[column] = ""
        data_frame["Trạng thái"] = data_frame["Trạng thái"].fillna("chưa nhận").astype(str)
        data_frame["Xác nhận đến"] = data_frame["Xác nhận đến"].fillna(False)
        return data_frame
    except: return pd.DataFrame(columns=required_columns)

def save_excel_safe(data_frame, file_path):
    directory_path = os.path.dirname(file_path)
    if directory_path and not os.path.exists(directory_path): os.makedirs(directory_path)
    data_frame.to_excel(file_path, index=False)

def get_avatar_url(name):
    return f"https://ui-avatars.com/api/?name={name}&background=0ea5e9&color=fff&size=128&bold=true"

# --- Session ---
def create_login_session(username):
    token = str(uuid.uuid4()); expiry_time = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, expiry_time)); connection.commit()
    return token

def verify_session_token(token):
    try:
        cursor.execute("SELECT username, expiry FROM sessions WHERE token=?", (token,))
        row = cursor.fetchone()
        if row and datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S") > datetime.now(): return row[0]
    except: pass
    return None

def initialize_session_state():
    if 'user' not in st.session_state:
        if "session" in st.query_params:
            token = st.query_params["session"]
            auto_username = verify_session_token(token)
            if auto_username:
                cursor.execute('SELECT * FROM users WHERE username=?', (auto_username,))
                user_data = cursor.fetchone()
                if user_data:
                    st.session_state.user=user_data[0]; st.session_state.role=user_data[2]; st.session_state.zalo=user_data[4]; st.session_state.wp_id=user_data[5]; st.session_state.expiry=user_data[8]; return
        st.session_state.user=None; st.session_state.role=None; st.session_state.zalo=None; st.session_state.wp_id=None; st.session_state.expiry=None

initialize_session_state()

# ==============================================================================
# 4. GIAO DIỆN CHAT (CÓ NÚT XÁC NHẬN)
# ==============================================================================
@st.fragment(run_every=3)
def render_chat_window(room_id, current_user_name, current_role, chat_mode="group"):
    try:
        # Lấy thêm cột ID để làm key cho nút bấm
        cursor.execute("SELECT id, sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,))
        messages = cursor.fetchall()[::-1]
    except: return

    chat_icon = "🏢" if chat_mode == "group" else "💬"
    display_name = room_id if chat_mode == "group" else "Tin nhắn riêng"
    st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:12px; margin-bottom:15px;'>{chat_icon} <b>{display_name}</b></div>", unsafe_allow_html=True)

    html_content = '<div class="chat-container">'
    
    # Chúng ta sẽ render HTML cho tin nhắn thường, nhưng dùng st.write cho tin nhắn có nút
    # Do đó ta không thể dùng 1 cục HTML lớn được. Ta sẽ loop và render từng cái.
    
    # Tuy nhiên để giữ layout đẹp (avatar, bubble), ta sẽ dùng st.chat_message tùy chỉnh hoặc columns
    # Cách tốt nhất trong Streamlit Fragments: Dùng st.chat_message kết hợp HTML
    
    last_sender = None
    for msg_id, sender, content, timestamp, msg_type in messages:
        is_me = (sender == current_user_name)
        
        # --- CSS WRAPPER CHO TỪNG TIN NHẮN ---
        alignment = "flex-end" if is_me else "flex-start"
        bg_color = "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)" if is_me else "#f1f5f9"
        text_color = "white" if is_me else "#1e293b"
        
        # Bắt đầu hàng
        with st.container():
            col1, col2 = st.columns([1, 15] if not is_me else [15, 1])
            
            # Nếu là người khác -> Hiện Avatar bên trái
            if not is_me:
                with col1:
                    if sender != last_sender:
                        st.image(get_avatar_url(sender), width=35)
            
            # Nội dung tin nhắn
            target_col = col2 if not is_me else col1
            with target_col:
                # Căn chỉnh
                st.markdown(f"""<style>div[data-testid="stVerticalBlock"] > div {{ align-items: {alignment}; display: flex; flex-direction: column; }}</style>""", unsafe_allow_html=True)
                
                # --- XỬ LÝ LOẠI TIN NHẮN ---
                
                # 1. Yêu cầu Thanh Toán (CÓ NÚT BẤM)
                if msg_type == 'payment_request':
                    amount = content
                    # Card Payment
                    st.markdown(f"""
                    <div class="payment-bubble" style="margin-bottom: 5px; align-self: {alignment};">
                        <div class="payment-header">💸 YÊU CẦU XÁC NHẬN</div>
                        <div>Quản lý {sender} đã chuyển khoản lương:</div>
                        <div class="payment-amount">{int(amount):,.0f} VNĐ</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Logic nút bấm: Chỉ hiện cho NHÂN VIÊN (người nhận) và không phải người gửi
                    if current_role == 'staff' and not is_me:
                        # Kiểm tra xem đã xác nhận chưa bằng cách đọc file Excel của chính mình
                        my_file = os.path.join(STORAGE_DIRECTORY, st.session_state.user, "salary.xlsx")
                        df_my = load_excel_safe(my_file)
                        
                        # Nếu còn dòng nào "chờ xác nhận" thì hiện nút
                        pending = len(df_my[df_my["Trạng thái"].astype(str).str.lower() == "chờ xác nhận"]) > 0
                        
                        if pending:
                            if st.button("✅ BẤM ĐỂ XÁC NHẬN ĐÃ NHẬN TIỀN", key=f"pay_btn_{msg_id}", use_container_width=False):
                                # Update Excel
                                df_my.loc[df_my["Trạng thái"].astype(str).str.lower() == "chờ xác nhận", "Trạng thái"] = "đã nhận"
                                save_excel_safe(df_my, my_file)
                                
                                # Gửi tin nhắn tự động
                                cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                               (room_id, current_user_name, f"✅ Đã xác nhận nhận đủ: {int(amount):,.0f} VNĐ", datetime.now().strftime("%H:%M"), "text"))
                                connection.commit()
                                st.rerun()
                        else:
                            st.caption("✅ Giao dịch đã hoàn tất")
                    else:
                        # Với Quản lý (người gửi)
                        st.caption("⏳ Đang chờ nhân viên xác nhận...")

                # 2. Hình ảnh
                elif msg_type == 'image':
                    if os.path.exists(content):
                        st.image(content, width=250)
                    else:
                        st.error("Ảnh đã xóa")

                # 3. Video Call
                elif msg_type == 'call':
                    link = content.split('|')[-1]
                    st.markdown(f"""
                    <div style="background:#e0f2fe; padding:10px; border-radius:10px; width:fit-content; align-self:{alignment};">
                        📹 <b>{sender}</b> đang gọi... <br>
                        <a href="{link}" target="_blank" style="font-weight:bold;">Tham gia ngay</a>
                    </div>
                    """, unsafe_allow_html=True)

                # 4. Tin nhắn thường
                else:
                    # Bubble HTML
                    st.markdown(f"""
                    <div class="bubble-{'right' if is_me else 'left'}" style="margin-bottom: 5px;">
                        {content}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Timestamp nhỏ
                st.caption(timestamp)

        last_sender = sender

# --- Dashboard ---
@st.fragment
def render_dashboard(staff_list):
    if not staff_list: st.warning("Chưa có nhân viên."); return
    total_debt = 0; staff_count = len(staff_list); pending_approval = 0
    
    for staff in staff_list:
        file_path = os.path.join(STORAGE_DIRECTORY, staff[0], "salary.xlsx")
        df = load_excel_safe(file_path)
        # Nợ: Chưa "đã nhận"
        if "Trạng thái" in df.columns:
            unpaid = df[~df["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)]
            total_debt += pd.to_numeric(unpaid["Tổng lương"], errors='coerce').sum()
        # Duyệt: Chưa xác nhận đến
        if "Xác nhận đến" in df.columns:
            pending_approval += len(df[df["Xác nhận đến"].astype(str).str.lower() == "false"])

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"""<div class="metric-card"><div class="metric-value">{staff_count}</div><div class="metric-label">Nhân sự</div></div>""", unsafe_allow_html=True)
    with c2: st.markdown(f"""<div class="metric-card"><div class="metric-value">{total_debt:,.0f}</div><div class="metric-label">Tổng Quỹ Lương</div></div>""", unsafe_allow_html=True)
    with c3:
        clr = "#ef4444" if pending_approval > 0 else "#22c55e"
        st.markdown(f"""<div class="metric-card"><div class="metric-value" style="color:{clr}">{pending_approval}</div><div class="metric-label">Ca chưa duyệt</div></div>""", unsafe_allow_html=True)
    st.write("")

# ==============================================================================
# 5. AUTH
# ==============================================================================
if st.session_state.user is None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #0ea5e9;'>💎 HỆ THỐNG V44</h1>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Đăng Nhập", "Đăng Ký", "Super Admin"])
        
        with t1:
            u = st.text_input("User"); p = st.text_input("Pass", type="password")
            if st.button("Login", type="primary", use_container_width=True):
                cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (u, p))
                ud = cursor.fetchone()
                if ud:
                    st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]
                    tk = create_login_session(ud[0]); st.query_params["session"] = tk; st.rerun()
                else: st.error("Sai thông tin")

        with t2:
            c_a, c_b = st.columns(2)
            with c_a: ru = st.text_input("User ID", key="r1"); rn = st.text_input("Tên hiển thị", key="r2"); rp = st.text_input("SĐT", key="r3")
            with c_b: rpass = st.text_input("Pass", type="password", key="r4"); rr = st.radio("Role", ["Nhân viên", "Quản lý"], horizontal=True)
            rwp = "ADMIN"; rk = ""
            if rr == "Nhân viên": rwp = st.text_input("Mã Chi Nhánh")
            elif rr == "Quản lý": rk = st.text_input("Key Admin", type="password")
            
            if st.button("Đăng Ký", use_container_width=True):
                if not ru or not rpass: st.warning("Điền đủ!")
                else:
                    try:
                        if rr == "Nhân viên" and not cursor.execute("SELECT id FROM workplaces WHERE id=?", (rwp,)).fetchone(): st.error("Mã CN sai!"); st.stop()
                        if rr == "Quản lý":
                            if not cursor.execute("SELECT key_code FROM license_keys WHERE key_code=? AND status='active'", (rk,)).fetchone(): st.error("Key sai!"); st.stop()
                            else: cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (rk,))
                        
                        op = os.path.join(STORAGE_DIRECTORY, ru)
                        if os.path.exists(op): shutil.rmtree(op)
                        cursor.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (ru, rpass, 'admin' if rr=="Quản lý" else 'staff', None, rn, rwp, rp, None, "2099-01-01"))
                        connection.commit(); st.success("OK! Đăng nhập ngay."); 
                    except sqlite3.IntegrityError: st.error("User đã tồn tại")

        with t3:
            su = st.text_input("Super User"); sp = st.text_input("Super Pass", type="password")
            if st.button("Super Login", use_container_width=True):
                if su == SUPER_ADMIN_USERNAME and sp == SUPER_ADMIN_PASSWORD:
                    st.session_state.user="SUPER_ADMIN"; st.session_state.role="super_admin"; st.session_state.zalo="System"; st.session_state.wp_id="MASTER"; st.rerun()
                else: st.error("Sai!")
    st.stop()

# ==============================================================================
# 6. MAIN APP
# ==============================================================================
cu = st.session_state.user; cr = st.session_state.role; cz = st.session_state.zalo; cwp = st.session_state.wp_id

with st.sidebar:
    st.image(get_avatar_url(cz), width=100); st.title(cz); st.caption(f"ID: {cu} | {cr}")
    if cwp and cwp not in ["ADMIN", "MASTER"]: st.caption(f"Chi nhánh: {cwp}")
    st.divider()
    if st.button("🚪 Đăng xuất", use_container_width=True):
        if "session" in st.query_params: cursor.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],)); connection.commit(); st.query_params.clear()
        st.session_state.user=None; st.rerun()

if cr == 'super_admin':
    st.header("🔧 SUPER ADMIN")
    t1, t2 = st.tabs(["Key", "Reset"])
    with t1:
        kt = st.selectbox("Loại Key", ["30 Ngày", "365 Ngày", "Vĩnh viễn"]); 
        if st.button("Sinh Key"): 
            k = str(uuid.uuid4())[:8].upper(); d = 36500 if kt == "Vĩnh viễn" else (365 if kt == "365 Ngày" else 30)
            cursor.execute("INSERT INTO license_keys VALUES (?,?,?)", (k, d, "active")); connection.commit(); st.success(f"Key: {k}")
        st.dataframe(pd.read_sql_query("SELECT * FROM license_keys", connection))
    with t2:
        if st.button("💣 RESET ALL"): 
            st.cache_resource.clear(); cursor.close(); connection.close()
            if os.path.exists(DATABASE_FILE): os.remove(DATABASE_FILE)
            if os.path.exists(STORAGE_DIRECTORY): shutil.rmtree(STORAGE_DIRECTORY); os.makedirs(STORAGE_DIRECTORY)
            if os.path.exists(UPLOAD_DIRECTORY): shutil.rmtree(UPLOAD_DIRECTORY); os.makedirs(UPLOAD_DIRECTORY)
            st.success("Đã Reset!"); st.stop()
    st.stop()

if cr == 'admin':
    dl = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if dl < 0:
        st.error(f"🔒 Hết hạn!"); k = st.text_input("Key:")
        if st.button("Kích hoạt"):
            kd = cursor.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (k,)).fetchone()
            if kd:
                n = (datetime.now()+timedelta(days=kd[0])).strftime("%Y-%m-%d")
                cursor.execute("UPDATE users SET expiry_date=? WHERE username=?", (n, cu)); cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (k,)); connection.commit(); st.session_state.expiry=n; st.success("OK"); time.sleep(1); st.rerun()
            else: st.error("Lỗi Key")
        st.stop()

tc, tw = st.tabs(["💬 Trung Tâm Liên Lạc", "📊 Quản Lý & Công Việc"])

with tc:
    cmode = st.radio("", ["🏢 Nhóm Chung", "👤 Nhắn Riêng"], horizontal=True, label_visibility="collapsed")
    aroom = None
    if cmode == "🏢 Nhóm Chung":
        if cr == 'admin':
            rms = [r[0] for r in cursor.execute("SELECT id FROM workplaces").fetchall()]
            aroom = st.selectbox("Chọn:", rms) if rms else None
        else: aroom = cwp
    else:
        us = [u[0] for u in cursor.execute("SELECT zalo_name FROM users WHERE username != ?", (cu,)).fetchall()]
        if us: tar = st.selectbox("Người nhắn:", us); aroom = f"DM_{sorted([cz, tar])[0]}_{sorted([cz, tar])[1]}"

    if aroom:
        # GỌI HÀM RENDER CHAT MỚI
        render_chat_window(aroom, cz, cr, "group" if cmode=="🏢 Nhóm Chung" else "private")
        
        c1, c2 = st.columns([6, 1])
        with c1:
            mi = st.chat_input("Nhập tin nhắn...")
            if mi: cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", (aroom, cz, mi, datetime.now().strftime("%H:%M"), "text")); connection.commit()
        with c2:
            with st.popover("➕", use_container_width=True):
                if st.button("📹 Call", use_container_width=True): lk = f"https://meet.jit.si/v_{uuid.uuid4()}"; cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (aroom, cz, f"v|{lk}", datetime.now().strftime("%H:%M"), "call")); connection.commit(); st.rerun()
                up = st.file_uploader("", type=['png','jpg'], label_visibility="collapsed")
                if up and st.button("Gửi Ảnh", use_container_width=True):
                    ext = up.name.split('.')[-1]; fname = f"{uuid.uuid4()}.{ext}"; p = os.path.join(UPLOAD_DIRECTORY, fname)
                    with open(p, "wb") as f: f.write(up.getbuffer())
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (aroom, cz, p, datetime.now().strftime("%H:%M"), "image")); connection.commit(); st.rerun()

with tw:
    if cr == 'admin':
        with st.expander("🏢 QUẢN LÝ CHI NHÁNH"):
            c1, c2 = st.columns(2)
            with c1: nid = st.text_input("Mã Mới").upper()
            with c2: nnm = st.text_input("Tên Hiển Thị")
            if st.button("Tạo Chi Nhánh"): 
                try: cursor.execute("INSERT INTO workplaces VALUES (?,?,?)", (nid, nnm, cu)); connection.commit(); st.success("OK"); st.rerun()
                except: st.error("Trùng mã")
        
        sl = cursor.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        render_dashboard(sl)
        
        if sl:
            st.divider(); sel = st.selectbox("📝 Quản lý:", [f"{s[1]} ({s[0]})" for s in sl]); tid = sel.split('(')[1].replace(')', '')
            tf = os.path.join(STORAGE_DIRECTORY, tid, "salary.xlsx"); dfs = load_excel_safe(tf)
            
            pcount = len(dfs[dfs["Xác nhận đến"].astype(str).str.lower() == "false"])
            cdebt = pd.to_numeric(dfs[~dfs["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)]["Tổng lương"], errors='coerce').sum()
            
            st.info(f"SĐT: {sl[[s[0] for s in sl].index(tid)][3]}")
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Nợ lương:", f"{cdebt:,.0f}")
            with c2: st.metric("Ca chưa duyệt:", f"{pcount}")
            with c3:
                if pcount > 0 and st.button("✅ DUYỆT CHẤM CÔNG", use_container_width=True):
                    dfs.loc[dfs["Xác nhận đến"].astype(str).str.lower() == "false", "Xác nhận đến"] = True
                    save_excel_safe(dfs, tf); st.success("Đã duyệt!"); time.sleep(1); st.rerun()
                
                if cdebt > 0 and st.button("💸 BÁO ĐÃ CHUYỂN KHOẢN", use_container_width=True):
                    # Cập nhật trạng thái
                    mask = ~dfs["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)
                    dfs.loc[mask, "Trạng thái"] = "chờ xác nhận"
                    save_excel_safe(dfs, tf)
                    
                    # GỬI TIN NHẮN TƯƠNG TÁC (LOẠI: payment_request)
                    twp = [s[2] for s in sl if s[0] == tid][0]
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                   (twp, cz, str(cdebt), datetime.now().strftime("%H:%M"), "payment_request"))
                    connection.commit()
                    st.success("Đã gửi yêu cầu xác nhận!"); st.rerun()
            
            with st.expander("➕ Thêm Ca"):
                with st.form("aa"):
                    d = st.date_input("Ngày"); v = st.text_input("VT", "Tại quán"); t1 = st.time_input("In"); t2 = st.time_input("Out"); r = st.number_input("Lương", 20000)
                    if st.form_submit_button("Lưu"):
                        dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                        if dt2 < dt1: dt2 += timedelta(days=1)
                        h = (dt2 - dt1).total_seconds() / 3600
                        new = pd.DataFrame([{"Ngày": d.strftime("%Y-%m-%d"), "Vị trí": v, "Giờ vào": t1.strftime("%H:%M"), "Giờ ra": t2.strftime("%H:%M"), "Tổng lương": h*r, "Trạng thái": "chưa nhận", "Xác nhận đến": True}])
                        dfs = pd.concat([dfs, new], ignore_index=True); save_excel_safe(dfs, tf); st.success("OK"); st.rerun()
            st.dataframe(dfs, use_container_width=True)

    elif cr == 'staff':
        mf = os.path.join(STORAGE_DIRECTORY, cu, "salary.xlsx"); dfm = load_excel_safe(mf)
        md = pd.to_numeric(dfm[~dfm["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)]["Tổng lương"], errors='coerce').sum()
        mp = len(dfm[dfm["Xác nhận đến"].astype(str).str.lower() == "false"]) if "Xác nhận đến" in dfm.columns else 0

        c1, c2 = st.columns(2)
        with c1: st.metric("💰 Quán nợ:", f"{md:,.0f}")
        with c2: st.metric("⏳ Chờ duyệt:", f"{mp}")
        
        if md > 0 and st.button("🔔 Đòi tiền", use_container_width=True):
            cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (cwp, cz, f"📣 Check lương: {md:,.0f}", datetime.now().strftime("%H:%M"), "text")); connection.commit(); st.toast("Sent!")
        
        with st.expander("➕ Báo cáo", expanded=True):
            with st.form("sa"):
                d = st.date_input("Ngày"); v = st.text_input("VT", cwp); t1 = st.time_input("In"); t2 = st.time_input("Out"); sr = st.number_input("Lương", 20000)
                if st.form_submit_button("Gửi"):
                    dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                    if dt2 < dt1: dt2 += timedelta(days=1)
                    h = (dt2 - dt1).total_seconds() / 3600
                    new = pd.DataFrame([{"Ngày": d.strftime("%Y-%m-%d"), "Vị trí": v, "Giờ vào": t1.strftime("%H:%M"), "Giờ ra": t2.strftime("%H:%M"), "Tổng lương": h*sr, "Trạng thái": "chưa nhận", "Xác nhận đến": False}])
                    dfm = pd.concat([dfm, new], ignore_index=True); save_excel_safe(dfm, mf); st.success("Lưu!"); st.rerun()
        st.dataframe(dfm, use_container_width=True)