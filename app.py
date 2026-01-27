import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
from datetime import datetime, timedelta

# ==========================================
# 1. CẤU HÌNH & CSS (LÀM ĐẸP GIAO DIỆN)
# ==========================================
st.set_page_config(page_title="Hệ Thống V25 Modern", layout="wide", page_icon="💎")

# CSS HACK ĐỂ GIAO DIỆN ĐẸP NHƯ APP
st.markdown("""
<style>
    /* 1. Tổng thể: Font chữ và Nền */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* 2. Chat Box: Làm đẹp khung chat */
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 5px !important;
    }
    
    /* Tin nhắn của User (Bên phải, màu xanh) */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        flex-direction: row-reverse;
        text-align: right;
    }
    div[data-testid="stChatMessage"]:nth-child(odd) .stMarkdown {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        padding: 10px 15px;
        border-radius: 20px 20px 0px 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        display: inline-block;
    }
    
    /* Tin nhắn của Bot/Người khác (Bên trái, màu trắng) */
    div[data-testid="stChatMessage"]:nth-child(even) {
        flex-direction: row;
        text-align: left;
    }
    div[data-testid="stChatMessage"]:nth-child(even) .stMarkdown {
        background: white;
        color: #333 !important;
        padding: 10px 15px;
        border-radius: 20px 20px 20px 0px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        display: inline-block;
    }

    /* 3. Nút bấm (Gradient đẹp) */
    .stButton>button {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 10px 24px;
        transition: all 0.3s ease;
        font-weight: bold;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }

    /* 4. Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }

    /* 5. Tag & Call Box */
    .tagged { 
        background-color: #fff3cd; 
        border-left: 5px solid #ffc107; 
        padding: 8px; 
        border-radius: 4px; 
        color: #856404;
        font-weight: 600;
        margin-bottom: 5px;
    }
    .call-box {
        background: linear-gradient(to right, #11998e, #38ef7d);
        color: white;
        padding: 12px;
        border-radius: 15px;
        text-align: center;
        margin: 5px 0;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .call-btn {
        background: white;
        color: #11998e;
        border: none;
        padding: 8px 16px;
        border-radius: 20px;
        cursor: pointer;
        font-weight: bold;
        margin-top: 5px;
        text-decoration: none;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE & LOGIC
# ==========================================
DB_FILE = "system_v25_modern.db" 
STORAGE = "user_files"
IMG_FOLDER = "chat_uploads"

if not os.path.exists(STORAGE): os.makedirs(STORAGE)
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

conn = get_connection()
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT, license_key TEXT, expiry_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS workplaces (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS license_keys (key_code TEXT PRIMARY KEY, duration_days INTEGER, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, workplace_id TEXT, sender TEXT, content TEXT, timestamp TEXT, msg_type TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT, expiry TEXT)''')
    conn.commit()
init_db()

SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

# --- UTILS ---
def find_col(df, keywords):
    if isinstance(keywords, str): keywords = [keywords]
    for col in df.columns:
        for key in keywords:
            if key.lower() in str(col).lower(): return col
    return None

def load_excel_safe(path):
    if not os.path.exists(path): return pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"])
    try: return pd.read_excel(path)
    except: return pd.DataFrame()

def create_session(username):
    token = str(uuid.uuid4()); exp = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, exp)); conn.commit()
    return token

def get_user_from_session(token):
    try:
        r = c.execute("SELECT username, expiry FROM sessions WHERE token=?", (token,)).fetchone()
        if r and datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S") > datetime.now(): return r[0]
    except: pass
    return None

if "session" in st.query_params:
    u = get_user_from_session(st.query_params["session"])
    if u and 'user' not in st.session_state:
        ud = c.execute('SELECT * FROM users WHERE username=?', (u,)).fetchone()
        if ud:
            st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]

# ==========================================
# 3. GIAO DIỆN CHAT (FRAGMENT - MƯỢT MÀ)
# ==========================================
@st.fragment(run_every=2)
def render_chat_box(room_id, current_user_zalo, chat_type="group"):
    try:
        msgs = c.execute("SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,)).fetchall()[::-1]
    except: return

    # Header đẹp
    icon = "🏢" if chat_type == "group" else "💬"
    room_name = room_id if chat_type == "group" else room_id.replace("DM_", "").replace(current_user_zalo, "").replace("_", "")
    st.markdown(f"<div style='text-align: center; color: #666; font-size: 0.9em; margin-bottom: 10px;'>{icon} Đang trò chuyện: <b>{room_name}</b></div>", unsafe_allow_html=True)

    with st.container(height=500):
        if not msgs: st.markdown("<div style='text-align: center; color: #999; padding: 20px;'>👋 Chưa có tin nhắn nào.</div>", unsafe_allow_html=True)
        
        for sender, content, ts, m_type in msgs:
            is_me = (sender == current_user_zalo)
            is_tagged = (m_type == 'text' and content and f"@{current_user_zalo}" in content)
            
            # Dùng st.chat_message nhưng đã được CSS Hack ở trên để đẹp hơn
            with st.chat_message("user" if is_me else "assistant", avatar="🧑‍💻" if is_me else "👤"):
                st.caption(f"{sender} • {ts}")
                
                if m_type == 'image':
                    if os.path.exists(content): st.image(content, width=300)
                elif m_type == 'emoji':
                    st.markdown(f"<h1 style='margin:0'>{content}</h1>", unsafe_allow_html=True)
                elif m_type == 'call':
                    # Giao diện Call Video đẹp
                    call_type = "📹 Video Call" if "video" in content else "📞 Voice Call"
                    link = content.split('|')[-1]
                    st.markdown(f"""
                    <div class="call-box">
                        <div><b>{sender}</b> đang gọi...</div>
                        <a href="{link}" target="_blank" class="call-btn">👉 Tham gia {call_type}</a>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if is_tagged: st.markdown(f'<div class="tagged">🔔 @{current_user_zalo}, bạn được nhắc:<br>{content}</div>', unsafe_allow_html=True)
                    else: st.write(content)

# ==========================================
# 4. TRANG LOGIN / REGISTER (GIAO DIỆN THẺ)
# ==========================================
if 'user' not in st.session_state:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #4b6cb7;'>🔐 ĐĂNG NHẬP HỆ THỐNG</h1>", unsafe_allow_html=True)
        tab_login, tab_reg = st.tabs(["Đăng Nhập", "Đăng Ký Mới"])
        
        with tab_login:
            with st.form("login_form"):
                u_l = st.text_input("Tên đăng nhập")
                p_l = st.text_input("Mật khẩu", type="password")
                if st.form_submit_button("🚀 Vào Hệ Thống", use_container_width=True):
                    ud = c.execute('SELECT * FROM users WHERE username=? AND password=?', (u_l, p_l)).fetchone()
                    if ud:
                        st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]
                        token = create_session(ud[0]); st.query_params["session"] = token
                        st.rerun()
                    elif u_l == SUPER_ADMIN_USER and p_l == SUPER_ADMIN_PASS:
                        st.session_state.user = "SUPER_ADMIN"; st.session_state.role = "super_admin"; st.rerun()
                    else: st.error("Sai thông tin!")

        with tab_reg:
            with st.form("reg_form"):
                c_a, c_b = st.columns(2)
                with c_a: u_r = st.text_input("User ID"); z_r = st.text_input("Tên Zalo"); p_r = st.text_input("SĐT")
                with c_b: pass_r = st.text_input("Pass", type="password"); r_r = st.radio("Vai trò", ["Nhân viên", "Quản lý"])
                wp_in = st.text_input("Mã Chi Nhánh (Nếu là NV)") if r_r == "Nhân viên" else "ADMIN"
                
                if st.form_submit_button("📝 Đăng Ký Ngay", use_container_width=True):
                    try:
                        if r_r == "Nhân viên" and not c.execute("SELECT id FROM workplaces WHERE id=?", (wp_in,)).fetchone():
                            st.error("Mã chi nhánh không đúng!"); st.stop()
                        c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (u_r, pass_r, 'admin' if r_r=="Quản lý" else 'staff', None, z_r, wp_in, p_r, None, "2000-01-01"))
                        conn.commit(); st.success("Thành công! Mời đăng nhập.")
                    except: st.error("ID đã tồn tại.")
    st.stop()

# ==========================================
# 5. KHU VỰC CHÍNH (SAU LOGIN)
# ==========================================
user = st.session_state.user; role = st.session_state.role
zalo = st.session_state.zalo if 'zalo' in st.session_state else user
wp_id = st.session_state.wp_id if 'wp_id' in st.session_state else ""

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
    st.title(f"{zalo}")
    st.info(f"Role: {role} | Work: {wp_id}")
    
    if st.button("🚪 Đăng xuất", use_container_width=True):
        if "session" in st.query_params: c.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],)); conn.commit(); st.query_params.clear()
        del st.session_state.user; st.rerun()

# --- SUPER ADMIN ---
if role == 'super_admin':
    st.header("🔑 QUẢN TRỊ VIÊN"); k_t = st.selectbox("Loại Key", [30, 365]); 
    if st.button("Sinh Key"): k = str(uuid.uuid4())[:8].upper(); c.execute("INSERT INTO license_keys VALUES (?,?,?)", (k, k_t, "active")); conn.commit(); st.success(f"Key: {k}")
    st.dataframe(pd.DataFrame(c.execute("SELECT * FROM license_keys").fetchall(), columns=["Key", "Days", "Status"])); st.stop()

# --- LICENSE CHECK ---
if role == 'admin':
    days = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if days < 0:
        st.error(f"🔒 Hết hạn!"); k_in = st.text_input("License Key:")
        if st.button("Kích hoạt"):
            d = c.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (k_in,)).fetchone()
            if d: nex = (datetime.now()+timedelta(days=d[0])).strftime("%Y-%m-%d"); c.execute("UPDATE users SET expiry_date=? WHERE username=?", (nex, user)); c.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (k_in,)); conn.commit(); st.session_state.expiry = nex; st.rerun()
            else: st.error("Key lỗi!")
        st.stop()

# --- MAIN UI ---
t_chat, t_work = st.tabs(["💬 Trò Chuyện & Gọi Điện", "📊 Quản Lý Công Việc"])

with t_chat:
    mode = st.radio("Chế độ:", ["🏢 Nhóm Chung", "👤 Nhắn Riêng"], horizontal=True, label_visibility="collapsed")
    active_room = None
    if mode == "🏢 Nhóm Chung":
        if role == 'admin':
            rooms = [r[0] for r in c.execute("SELECT id FROM workplaces").fetchall()]
            if rooms: active_room = st.selectbox("Chọn nhóm:", rooms)
        else: active_room = wp_id
    else:
        users = [u[0] for u in c.execute("SELECT zalo_name FROM users WHERE username != ?", (user,)).fetchall()]
        if users:
            target = st.selectbox("Người nhắn:", users)
            active_room = f"DM_{sorted([zalo, target])[0]}_{sorted([zalo, target])[1]}"
    
    if active_room:
        render_chat_box(active_room, zalo, "private" if mode == "👤 Nhắn Riêng" else "group")
        
        c1, c2 = st.columns([5, 1])
        with c1:
            if p := st.chat_input("Nhập tin nhắn..."):
                c.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", (active_room, zalo, p, datetime.now().strftime("%H:%M"), "text")); conn.commit()
        with c2:
            with st.popover("➕ Tiện ích", use_container_width=True):
                if st.button("📹 Video Call", use_container_width=True):
                     link = f"https://meet.jit.si/video_{uuid.uuid4()}"; c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, f"v|{link}", datetime.now().strftime("%H:%M"), "call")); conn.commit(); st.rerun()
                st.divider()
                st.write("Gửi nhanh:")
                ec = st.columns(4)
                for i,e in enumerate(["👍","❤️","😂","OK"]): 
                    if ec[i].button(e): c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, e, datetime.now().strftime("%H:%M"), "emoji")); conn.commit(); st.rerun()
                img = st.file_uploader("", type=['png','jpg'], label_visibility="collapsed")
                if img and st.button("Gửi Ảnh"):
                    ext = img.name.split('.')[-1]; fname = f"{uuid.uuid4()}.{ext}"; fpath = os.path.join(IMG_FOLDER, fname); 
                    with open(fpath, "wb") as f: f.write(img.getbuffer())
                    c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, fpath, datetime.now().strftime("%H:%M"), "image")); conn.commit(); st.rerun()

with t_work:
    if role == 'admin':
        with st.expander("🏢 CẤU HÌNH CHI NHÁNH"):
            ni = st.text_input("Mã ID").upper(); nn = st.text_input("Tên")
            if st.button("Tạo"): 
                try: c.execute("INSERT INTO workplaces VALUES (?,?,?)", (ni, nn, user)); conn.commit(); st.success(f"Tạo {ni}"); st.rerun()
                except: st.error("Trùng mã!")
            st.dataframe(pd.DataFrame(c.execute("SELECT id, name FROM workplaces").fetchall(), columns=["ID", "Name"]))
        
        staffs = c.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        total = sum([pd.to_numeric(load_excel_safe(os.path.join(STORAGE, s[0], "salary.xlsx"))[lambda d: d[find_col(d, "trạng thái")].astype(str).str.lower().str.contains("chưa", na=False)][find_col(load_excel_safe(os.path.join(STORAGE, s[0], "salary.xlsx")), "tổng")], errors='coerce').sum() for s in staffs]) if staffs else 0
        st.metric("TỔNG NỢ LƯƠNG", f"{total:,.0f} VNĐ")

        if staffs:
            sel = st.selectbox("Chọn NV", [f"{s[1]} ({s[0]})" for s in staffs]); uid = sel.split("(")[1].replace(")","")
            p_path = os.path.join(STORAGE, uid, "salary.xlsx"); df = load_excel_safe(p_path)
            c_tt = find_col(df, "trạng thái"); c_tl = find_col(df, "tổng"); debt = pd.to_numeric(df[df[c_tt].astype(str).str.lower().str.contains("chưa", na=False)][c_tl], errors='coerce').sum() if c_tt else 0
            
            c1, c2 = st.columns([2,1]); c1.write(f"Nợ: {debt:,.0f} VNĐ")
            if debt > 0 and c2.button("Thanh toán"):
                df.loc[df[c_tt].astype(str).str.lower().str.contains("chưa", na=False), c_tt] = "nhận"; df.to_excel(p_path, index=False)
                c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", ([s[2] for s in staffs if s[0]==uid][0], zalo, f"✅ Đã trả {debt:,.0f}", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.rerun()
            
            with st.expander("Thêm ca"):
                with st.form("a"):
                    d = st.date_input("Ngày"); v = st.text_input("VT"); t1=st.time_input("In"); t2=st.time_input("Out"); l=st.number_input("Lương", 20000)
                    if st.form_submit_button("Lưu"):
                        s=datetime.combine(d,t1); e=datetime.combine(d,t2); 
                        if e<s: e+=timedelta(days=1)
                        pd.concat([df, pd.DataFrame([{find_col(df,"ngày"):"%s"%d, find_col(df,"vị trí"):v, find_col(df,"tổng"):(e-s).seconds/3600*l, "Trạng thái":"chưa nhận", find_col(df,"vào"):"%s"%t1, find_col(df,"ra"):"%s"%t2, "Xác nhận đến":False}])], ignore_index=True).to_excel(p_path, index=False); st.rerun()
            st.dataframe(df)

    elif role == 'staff':
        p = os.path.join(STORAGE, user); f = os.path.join(p, "salary.xlsx"); df = load_excel_safe(f)
        c_tt = find_col(df, "trạng thái"); c_tl = find_col(df, "tổng")
        due = pd.to_numeric(df[df[c_tt].astype(str).str.lower().str.contains("chưa", na=False)][c_tl], errors='coerce').sum() if c_tt else 0
        c1, c2 = st.columns([2,1]); c1.metric("Nợ bạn", f"{due:,.0f} VNĐ")
        if due > 0 and c2.button("Đòi tiền"): c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (wp_id, zalo, f"📣 Trả {due:,.0f} đi!", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.toast("Đã gửi!")
        
        with st.form("s"):
            d=st.date_input("Ngày"); v=st.text_input("VT", wp_id); t1=st.time_input("In"); t2=st.time_input("Out")
            if st.form_submit_button("Lưu"):
                s=datetime.combine(d,t1); e=datetime.combine(d,t2); 
                if e<s: e+=timedelta(days=1)
                pd.concat([df, pd.DataFrame([{find_col(df,"ngày"):"%s"%d, find_col(df,"vị trí"):v, find_col(df,"tổng"):(e-s).seconds/3600*20000, "Trạng thái":"chưa nhận", find_col(df,"vào"):"%s"%t1, find_col(df,"ra"):"%s"%t2, "Xác nhận đến":False}])], ignore_index=True).to_excel(f, index=False); st.rerun()
        st.dataframe(df)