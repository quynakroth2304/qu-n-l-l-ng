import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
from datetime import datetime, timedelta

# ==========================================
# 1. CẤU HÌNH & CSS "MODERN ERA"
# ==========================================
st.set_page_config(page_title="Hệ Thống V28 Modern", layout="wide", page_icon="✨", initial_sidebar_state="expanded")

# Tên DB mới
DB_FILE = "system_v28_modern.db"
STORAGE = "user_files"
IMG_FOLDER = "chat_uploads"

if not os.path.exists(STORAGE): os.makedirs(STORAGE)
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

# --- SIÊU CSS (LÀM ĐẸP TOÀN DIỆN) ---
st.markdown("""
<style>
    /* Import Font hiện đại */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Ẩn Header/Footer mặc định của Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Tùy chỉnh thanh cuộn (Scrollbar) */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #888; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #555; }

    /* CARD DASHBOARD (Thẻ thống kê) */
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        transition: transform 0.2s;
        text-align: center;
    }
    .metric-card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }
    .metric-value { font-size: 24px; font-weight: 800; color: #2c3e50; }
    .metric-label { font-size: 14px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; }

    /* CHAT UI CẢI TIẾN */
    .chat-container {
        padding: 15px;
        background: #f8f9fa;
        border-radius: 20px;
        height: 65vh;
        overflow-y: auto;
        border: 1px solid #e9ecef;
    }
    
    /* Tin nhắn User (Phải) */
    .msg-right { display: flex; justify-content: flex-end; margin-bottom: 10px; }
    .bubble-right {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 10px 16px;
        border-radius: 18px 18px 4px 18px;
        box-shadow: 0 2px 5px rgba(118, 75, 162, 0.3);
        max-width: 75%;
        font-size: 14px;
    }

    /* Tin nhắn Others (Trái) */
    .msg-left { display: flex; justify-content: flex-start; margin-bottom: 10px; align-items: flex-end;}
    .bubble-left {
        background: white;
        color: #333;
        padding: 10px 16px;
        border-radius: 18px 18px 18px 4px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        max-width: 75%;
        font-size: 14px;
    }
    .avatar-icon {
        width: 30px; height: 30px; border-radius: 50%; 
        margin-right: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }

    /* NÚT BẤM HIỆN ĐẠI */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        border: none;
        transition: all 0.3s;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover { opacity: 0.9; transform: scale(1.02); }

    /* CALL CARD */
    .call-box {
        background: #e8f5e9; border-left: 4px solid #00c853;
        padding: 10px; border-radius: 8px; width: fit-content;
    }
    .call-link {
        text-decoration: none; color: white; background: #00c853;
        padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold;
        display: inline-block; margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE CORE
# ==========================================
@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

conn = get_connection()
c = conn.cursor()

def init_db():
    tables = [
        '''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT, license_key TEXT, expiry_date TEXT)''',
        '''CREATE TABLE IF NOT EXISTS workplaces (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''',
        '''CREATE TABLE IF NOT EXISTS license_keys (key_code TEXT PRIMARY KEY, duration_days INTEGER, status TEXT)''',
        '''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, workplace_id TEXT, sender TEXT, content TEXT, timestamp TEXT, msg_type TEXT)''',
        '''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT, expiry TEXT)'''
    ]
    for t in tables: c.execute(t)
    conn.commit()
init_db()

SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

# --- UTILS ---
def load_excel_safe(path):
    cols = ["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]
    if not os.path.exists(path): return pd.DataFrame(columns=cols)
    try:
        df = pd.read_excel(path)
        for col in cols: 
            if col not in df.columns: df[col] = ""
        return df
    except: return pd.DataFrame(columns=cols)

def get_avatar(name):
    return f"https://api.dicebear.com/7.x/notionists/svg?seed={name}&backgroundColor=b6e3f4"

def create_session(u):
    t = str(uuid.uuid4()); e = (datetime.now()+timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (t, u, e)); conn.commit()
    return t

if "session" in st.query_params:
    u = c.execute("SELECT username FROM sessions WHERE token=?", (st.query_params["session"],)).fetchone()
    if u and 'user' not in st.session_state:
        ud = c.execute('SELECT * FROM users WHERE username=?', (u[0],)).fetchone()
        if ud: st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]

# ==========================================
# 3. FRAGMENTS (CÁC PHẦN TỬ UI KHÔNG LOAD LẠI TRANG)
# ==========================================

# --- 3.1 CHAT BOX MƯỢT MÀ ---
@st.fragment(run_every=2)
def render_chat_modern(room_id, my_name, chat_type="group"):
    try:
        msgs = c.execute("SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,)).fetchall()[::-1]
    except: return

    # Header
    st.markdown(f"<div style='margin-bottom:10px; color:#888; font-size:12px; text-align:center'>🔒 Tin nhắn được mã hóa đầu cuối tại <b>{room_id}</b></div>", unsafe_allow_html=True)
    
    html = '<div class="chat-container">'
    last = None
    
    for sender, content, ts, m_type in msgs:
        is_me = (sender == my_name)
        
        # Row Start
        if is_me:
            html += '<div class="msg-right">'
            body = f'<div class="bubble-right" title="{ts}">'
        else:
            html += '<div class="msg-left">'
            if sender != last: html += f'<img src="{get_avatar(sender)}" class="avatar-icon" title="{sender}">'
            else: html += '<div style="width:38px"></div>' # Spacer
            body = f'<div class="bubble-left" title="{ts}">'
            if chat_type=="group" and sender!=last: body = f'<div style="font-size:10px; color:#888; margin-bottom:2px">{sender}</div>' + body

        # Content
        if m_type == 'image':
            import base64
            if os.path.exists(content):
                with open(content, "rb") as f: b64 = base64.b64encode(f.read()).decode()
                body += f'<img src="data:image/png;base64,{b64}" style="max-width:200px; border-radius:10px;">'
            else: body += "⚠️ Ảnh lỗi"
        elif m_type == 'emoji':
            body = body.replace("bubble-left", "").replace("bubble-right", "") # Remove bubble bg for emoji
            body += f'<div style="font-size:32px">{content}</div>'
        elif m_type == 'call':
            link = content.split('|')[-1]
            icon = "📹" if "video" in content else "📞"
            body += f'<div class="call-box"><div>{icon} <b>{sender}</b> đang gọi...</div><a href="{link}" target="_blank" class="call-link">Tham gia ngay</a></div>'
        else:
            if f"@{my_name}" in content: content = f"<span style='background:#fff3cd;padding:2px'><b>{content}</b></span>"
            body += content
        
        html += body + '</div></div>' # End bubble & row
        last = sender

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("<script>var e=window.parent.document.querySelector('.chat-container');if(e)e.scrollTop=e.scrollHeight;</script>", unsafe_allow_html=True)

# --- 3.2 DASHBOARD ADMIN (CARD STYLE) ---
@st.fragment
def render_admin_dashboard(staffs):
    if not staffs:
        st.warning("Chưa có nhân viên nào.")
        return

    # Tính toán số liệu
    total_debt = 0
    active_staff = len(staffs)
    alerts = 0
    now = datetime.now()

    for s in staffs:
        path = os.path.join(STORAGE, s[0], "salary.xlsx")
        df = load_excel_safe(path)
        # Tính nợ
        if "Trạng thái" in df.columns and "Tổng lương" in df.columns:
            debt = pd.to_numeric(df[df["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
            total_debt += debt
        # Cảnh báo
        if "Ngày" in df.columns and "Giờ vào" in df.columns:
            today_str = now.strftime("%Y-%m-%d")
            shifts = df[df["Ngày"].astype(str).str.contains(today_str, na=False)]
            if not shifts.empty: alerts += 1 # Đếm số người có ca hôm nay

    # Hiển thị Card
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{active_staff}</div><div class="metric-label">Nhân sự</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{total_debt:,.0f}</div><div class="metric-label">Tổng Quỹ Lương (VNĐ)</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{alerts}</div><div class="metric-label">Ca làm hôm nay</div></div>""", unsafe_allow_html=True)
    
    st.write("") # Spacer

# ==========================================
# 4. AUTHENTICATION (LOGIN/REGISTER)
# ==========================================
if 'user' not in st.session_state:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>🌐 HỆ THỐNG V28</h1>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["Đăng nhập", "Đăng ký", "Super Admin"])
        
        with tab3:
            sa_u = st.text_input("User Super"); sa_p = st.text_input("Pass Super", type="password")
            if st.button("🚀 Login Super", use_container_width=True):
                if sa_u == SUPER_ADMIN_USER and sa_p == SUPER_ADMIN_PASS:
                    st.session_state.user="SUPER_ADMIN"; st.session_state.role="super_admin"; st.rerun()
                else: st.error("Sai!")

        with tab1:
            u = st.text_input("Tên đăng nhập")
            p = st.text_input("Mật khẩu", type="password")
            if st.button("Đăng nhập", use_container_width=True):
                ud = c.execute('SELECT * FROM users WHERE username=? AND password=?', (u, p)).fetchone()
                if ud:
                    st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]
                    tk = create_session(ud[0]); st.query_params["session"] = tk; st.rerun()
                else: st.error("Sai thông tin!")

        with tab2:
            c_a, c_b = st.columns(2)
            with c_a: u_r = st.text_input("User ID", key="r1"); z_r = st.text_input("Tên hiển thị", key="r2")
            with c_b: p_r = st.text_input("Pass", type="password", key="r3"); ph_r = st.text_input("SĐT", key="r4")
            r_r = st.radio("Vai trò", ["Nhân viên", "Quản lý"], horizontal=True)
            wp = st.text_input("Mã Chi Nhánh (Nếu là NV)") if r_r == "Nhân viên" else "ADMIN"
            
            if st.button("Tạo tài khoản", use_container_width=True):
                try:
                    if r_r=="Nhân viên" and not c.execute("SELECT id FROM workplaces WHERE id=?", (wp,)).fetchone(): st.error("Mã CN không đúng!"); st.stop()
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (u_r, p_r, 'admin' if r_r=="Quản lý" else 'staff', None, z_r, wp, ph_r, None, "2000-01-01"))
                    conn.commit(); st.success("Thành công! Mời đăng nhập.")
                except: st.error("ID đã tồn tại.")
    st.stop()

# ==========================================
# 5. MAIN APP
# ==========================================
user = st.session_state.user; role = st.session_state.role; zalo = st.session_state.zalo; wp_id = st.session_state.wp_id

# SIDEBAR
with st.sidebar:
    st.image(get_avatar(zalo), width=100)
    st.title(zalo)
    st.caption(f"Role: {role} • {wp_id}")
    if st.button("Đăng xuất", use_container_width=True):
        if "session" in st.query_params: c.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],)); conn.commit(); st.query_params.clear()
        del st.session_state.user; st.rerun()

# SUPER ADMIN ZONE
if role == 'super_admin':
    st.header("🔧 SUPER ADMIN"); 
    t1, t2 = st.tabs(["Key", "Reset"])
    with t1:
        if st.button("Tạo Key 1 Năm"): k=str(uuid.uuid4())[:8].upper(); c.execute("INSERT INTO license_keys VALUES (?,?,?)", (k, 365, "active")); conn.commit(); st.success(k)
        st.dataframe(pd.DataFrame(c.execute("SELECT * FROM license_keys").fetchall(), columns=["Key", "Days", "Status"]))
    with t2:
        if st.button("RESET TOÀN BỘ DATA"): st.cache_resource.clear(); c.close(); conn.close(); os.remove(DB_FILE); st.success("Xong! F5 lại."); st.stop()
    st.stop()

# ADMIN LICENSE CHECK
if role == 'admin':
    days = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if days < 0:
        st.error("🔒 Hết hạn!"); k=st.text_input("Key:"); 
        if st.button("Kích hoạt"):
            d=c.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (k,)).fetchone()
            if d: n=(datetime.now()+timedelta(days=d[0])).strftime("%Y-%m-%d"); c.execute("UPDATE users SET expiry_date=? WHERE username=?", (n, user)); c.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (k,)); conn.commit(); st.session_state.expiry=n; st.rerun()
            else: st.error("Lỗi")
        st.stop()

# --- MAIN TABS ---
tab_chat, tab_work = st.tabs(["💬 Trung Tâm Liên Lạc", "📊 Điều Hành"])

with tab_chat:
    mode = st.radio("", ["🏢 Nhóm Chung", "👤 Nhắn Riêng"], horizontal=True, label_visibility="collapsed")
    active_room = None
    
    if mode == "🏢 Nhóm Chung":
        if role == 'admin':
            rms = [r[0] for r in c.execute("SELECT id FROM workplaces").fetchall()]
            active_room = st.selectbox("Chọn chi nhánh:", rms) if rms else None
        else: active_room = wp_id
    else:
        us = [u[0] for u in c.execute("SELECT zalo_name FROM users WHERE username != ?", (user,)).fetchall()]
        if us: target = st.selectbox("Chọn người nhắn:", us); active_room = f"DM_{sorted([zalo, target])[0]}_{sorted([zalo, target])[1]}"

    if active_room:
        render_chat_modern(active_room, zalo, "group" if mode=="🏢 Nhóm Chung" else "private")
        
        c1, c2 = st.columns([6, 1])
        with c1:
            if p := st.chat_input("Nhập tin nhắn..."):
                c.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", (active_room, zalo, p, datetime.now().strftime("%H:%M"), "text")); conn.commit()
        with c2:
            with st.popover("➕"):
                if st.button("📹 Video Call", use_container_width=True): 
                    link=f"https://meet.jit.si/v_{uuid.uuid4()}"; c.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (active_room, zalo, f"v|{link}", datetime.now().strftime("%H:%M"), "call")); conn.commit(); st.rerun()
                img = st.file_uploader("", type=['png','jpg'], label_visibility="collapsed")
                if img and st.button("Gửi Ảnh", use_container_width=True):
                    ext = img.name.split('.')[-1]; fname = f"{uuid.uuid4()}.{ext}"; fpath = os.path.join(IMG_FOLDER, fname); 
                    with open(fpath, "wb") as f: f.write(img.getbuffer())
                    c.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (active_room, zalo, fpath, datetime.now().strftime("%H:%M"), "image")); conn.commit(); st.rerun()

with tab_work:
    if role == 'admin':
        # CẤU HÌNH
        with st.expander("⚙️ CẤU HÌNH CHI NHÁNH", expanded=False):
            ni = st.text_input("Mã CN Mới"); nn = st.text_input("Tên CN")
            if st.button("Tạo"): 
                try: c.execute("INSERT INTO workplaces VALUES (?,?,?)", (ni, nn, user)); conn.commit(); st.success("OK"); st.rerun()
                except: st.error("Trùng")
        
        staffs = c.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        
        # DASHBOARD CARD
        render_admin_dashboard(staffs)
        
        if staffs:
            st.divider()
            sel = st.selectbox("📝 Quản lý nhân viên:", [f"{s[1]} ({s[0]})" for s in staffs]); uid = sel.split("(")[1].replace(")","")
            p_path = os.path.join(STORAGE, uid, "salary.xlsx"); df = load_excel_safe(p_path)
            
            # Tính nợ
            debt = 0
            if "Trạng thái" in df.columns:
                debt = pd.to_numeric(df[df["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
            
            c1, c2 = st.columns([2, 1])
            with c1: st.metric("Nợ nhân viên này:", f"{debt:,.0f} VNĐ")
            with c2: 
                if debt > 0 and st.button("💸 Thanh Toán Ngay", use_container_width=True):
                    df.loc[df["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False), "Trạng thái"] = "nhận"; df.to_excel(p_path, index=False)
                    c.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", ([s[2] for s in staffs if s[0]==uid][0], zalo, f"✅ Đã trả lương: {debt:,.0f}", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.rerun()
            
            with st.expander("➕ Thêm Ca Làm Việc"):
                with st.form("adm_add"):
                    d = st.date_input("Ngày"); v = st.text_input("Vị trí", "Tại quán")
                    t1 = st.time_input("Vào"); t2 = st.time_input("Ra"); l = st.number_input("Lương/h", 20000)
                    if st.form_submit_button("Lưu Ca", use_container_width=True):
                        s=datetime.combine(d,t1); e=datetime.combine(d,t2); 
                        if e<s: e+=timedelta(days=1)
                        h = (e-s).total_seconds()/3600
                        new = pd.DataFrame([{"Ngày":d.strftime("%Y-%m-%d"), "Vị trí":v, "Giờ vào":t1.strftime("%H:%M"), "Giờ ra":t2.strftime("%H:%M"), "Tổng lương":h*l, "Trạng thái":"chưa nhận", "Xác nhận đến":False}])
                        pd.concat([df, new], ignore_index=True).to_excel(p_path, index=False); st.success("OK"); st.rerun()
            
            st.dataframe(df, use_container_width=True)

    elif role == 'staff':
        # GIAO DIỆN NHÂN VIÊN
        p = os.path.join(STORAGE, user, "salary.xlsx"); df = load_excel_safe(p)
        debt = 0
        if "Trạng thái" in df.columns:
            debt = pd.to_numeric(df[df["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
        
        c1, c2 = st.columns(2)
        with c1: st.metric("💰 Quán đang nợ bạn", f"{debt:,.0f} VNĐ")
        with c2: 
            if debt > 0 and st.button("🔔 Đòi tiền ngay", use_container_width=True): 
                c.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (wp_id, zalo, f"📣 Anh ơi check lương em: {debt:,.0f}", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.toast("Đã gửi!")
        
        with st.expander("➕ Báo cáo ca làm", expanded=True):
            with st.form("st_add"):
                d = st.date_input("Ngày"); v = st.text_input("Vị trí", wp_id)
                t1 = st.time_input("Vào"); t2 = st.time_input("Ra")
                if st.form_submit_button("Lưu Ca", use_container_width=True):
                    s=datetime.combine(d,t1); e=datetime.combine(d,t2); 
                    if e<s: e+=timedelta(days=1)
                    h = (e-s).total_seconds()/3600
                    new = pd.DataFrame([{"Ngày":d.strftime("%Y-%m-%d"), "Vị trí":v, "Giờ vào":t1.strftime("%H:%M"), "Giờ ra":t2.strftime("%H:%M"), "Tổng lương":h*20000, "Trạng thái":"chưa nhận", "Xác nhận đến":False}])
                    pd.concat([df, new], ignore_index=True).to_excel(p, index=False); st.success("Đã lưu!"); st.rerun()
        st.dataframe(df, use_container_width=True)