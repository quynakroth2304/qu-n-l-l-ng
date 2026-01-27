import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
import shutil
from datetime import datetime, timedelta

# ==============================================================================
# 1. CẤU HÌNH & GIAO DIỆN (V41 NATURAL FLOW)
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống V41 Natural", 
    layout="wide", 
    page_icon="💎", 
    initial_sidebar_state="expanded"
)

# --- THIẾT LẬP FILE & DATABASE ---
DB_FILE = "system_v41_natural.db"
STORAGE_DIR = "user_files"
UPLOAD_DIR = "chat_uploads"

if not os.path.exists(STORAGE_DIR): os.makedirs(STORAGE_DIR)
if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)

# --- CSS FIX LỖI XUỐNG DÒNG (QUAN TRỌNG NHẤT) ---
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

    /* --- KHUNG CHAT (FIX LỖI CẮT CHỮ) --- */
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
        margin-bottom: 8px;
        width: 100%;
    }

    /* Tin nhắn Phải (Tôi) */
    .msg-right {
        justify-content: flex-end;
    }
    .bubble-right {
        background: linear-gradient(135deg, #0084ff 0%, #0078e7 100%);
        color: white;
        padding: 10px 16px;
        border-radius: 18px 18px 4px 18px;
        
        /* CẤU HÌNH TRÀN DÒNG TỰ NHIÊN */
        max-width: 85%; /* Mở rộng tối đa */
        width: fit-content;
        
        /* Chỉ xuống dòng khi hết chỗ hoặc gặp dấu cách */
        word-wrap: break-word; 
        overflow-wrap: break-word;
        word-break: normal; /* KHÔNG cắt ngang từ */
        white-space: pre-wrap; /* Giữ dấu Enter nếu người dùng bấm */
        
        font-size: 15px;
        line-height: 1.4;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    /* Tin nhắn Trái (Người khác) */
    .msg-left {
        justify-content: flex-start;
    }
    .bubble-left {
        background: #e4e6eb;
        color: #050505;
        padding: 10px 16px;
        border-radius: 18px 18px 18px 4px;
        
        /* CẤU HÌNH TRÀN DÒNG TỰ NHIÊN */
        max-width: 85%; /* Mở rộng tối đa */
        width: fit-content;
        
        word-wrap: break-word;
        overflow-wrap: break-word;
        word-break: normal; /* KHÔNG cắt ngang từ */
        white-space: pre-wrap;
        
        font-size: 15px;
        line-height: 1.4;
    }
    
    .chat-avatar {
        width: 32px; height: 32px; border-radius: 50%;
        margin-right: 8px; flex-shrink: 0;
        object-fit: cover;
    }

    /* Metric Card */
    .metric-card {
        background: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #f0f0f0;
        text-align: center;
    }
    .metric-value { font-size: 28px; font-weight: 700; color: #0ea5e9; margin-bottom: 5px; }
    .metric-label { font-size: 13px; color: #64748b; font-weight: 600; text-transform: uppercase; }

    /* Button */
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

# --- Utils ---
def load_excel_safe(file_path):
    cols = ["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]
    if not os.path.exists(file_path): return pd.DataFrame(columns=cols)
    try:
        df = pd.read_excel(file_path)
        for c in cols: 
            if c not in df.columns: df[c] = ""
        df["Xác nhận đến"] = df["Xác nhận đến"].fillna(False)
        return df
    except: return pd.DataFrame(columns=cols)

def save_excel_safe(dataframe, file_path):
    d = os.path.dirname(file_path)
    if d and not os.path.exists(d): os.makedirs(d)
    dataframe.to_excel(file_path, index=False)

def get_avatar_url(name):
    return f"https://ui-avatars.com/api/?name={name}&background=0ea5e9&color=fff&size=128&bold=true"

# --- Session ---
def create_login_session(username):
    token = str(uuid.uuid4()); exp = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, exp)); conn.commit()
    return token

def verify_session_token(token):
    try:
        r = cursor.execute("SELECT username, expiry FROM sessions WHERE token=?", (token,)).fetchone()
        if r and datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S") > datetime.now(): return r[0]
    except: pass
    return None

if "session" in st.query_params:
    token = st.query_params["session"]
    auto_user = verify_session_token(token)
    if auto_user and 'user' not in st.session_state:
        ud = cursor.execute('SELECT * FROM users WHERE username=?', (auto_user,)).fetchone()
        if ud:
            st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]

# ==============================================================================
# 3. GIAO DIỆN CHAT (RENDER)
# ==============================================================================
@st.fragment(run_every=2)
def render_chat_window(room_id, current_user_name, chat_mode="group"):
    try:
        cursor.execute("SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,))
        messages = cursor.fetchall()[::-1]
    except: return

    icon = "🏢" if chat_mode == "group" else "💬"
    display = room_id if chat_mode == "group" else "Tin nhắn riêng"
    st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:12px; margin-bottom:15px;'>{icon} <b>{display}</b></div>", unsafe_allow_html=True)

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
                with open(content, "rb") as f: b64 = base64.b64encode(f.read()).decode()
                msg_body = f'<img src="data:image/png;base64,{b64}" style="max-width:250px; border-radius:12px;">'
            else: msg_body = "<i>⚠️ Ảnh đã xóa</i>"
        elif msg_type == 'emoji':
            msg_body = f'<div style="font-size:40px; line-height:1;">{content}</div>'
        elif msg_type == 'call':
            link = content.split('|')[-1]; icon_c = "📹" if "video" in content else "📞"
            msg_body = f'<div style="background:#e0f2fe; padding:10px; border-radius:10px; border:1px solid #bae6fd;"><div style="font-size:18px; margin-bottom:5px;">{icon_c} <b>{sender}</b> đang gọi...</div><a href="{link}" target="_blank" style="background:#0284c7; color:white; padding:5px 15px; border-radius:20px; text-decoration:none; font-weight:bold; font-size:12px;">Tham gia ngay</a></div>'
        else:
            # Text
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

@st.fragment
def render_dashboard(staff_list):
    if not staff_list: st.warning("Chưa có nhân viên."); return
    debt = 0; count = len(staff_list); pending = 0; today = datetime.now().strftime("%Y-%m-%d")
    for s in staff_list:
        df = load_excel_safe(os.path.join(STORAGE_DIR, s[0], "salary.xlsx"))
        if "Trạng thái" in df.columns: debt += pd.to_numeric(df[df["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
        if "Xác nhận đến" in df.columns: pending += len(df[df["Xác nhận đến"].astype(str).str.lower() == "false"])
    
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"""<div class="metric-card"><div class="metric-value">{count}</div><div class="metric-label">Nhân sự</div></div>""", unsafe_allow_html=True)
    with c2: st.markdown(f"""<div class="metric-card"><div class="metric-value">{debt:,.0f}</div><div class="metric-label">Tổng Quỹ Lương</div></div>""", unsafe_allow_html=True)
    with c3:
        clr = "#ef4444" if pending > 0 else "#22c55e"
        st.markdown(f"""<div class="metric-card"><div class="metric-value" style="color:{clr}">{pending}</div><div class="metric-label">Ca chưa xác nhận</div></div>""", unsafe_allow_html=True)
    st.write("")

# ==============================================================================
# 4. AUTHENTICATION
# ==============================================================================
if 'user' not in st.session_state:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #0ea5e9;'>💎 HỆ THỐNG V41</h1>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Đăng Nhập", "Đăng Ký", "Super Admin"])
        
        with t1:
            u = st.text_input("User"); p = st.text_input("Pass", type="password")
            if st.button("Đăng nhập", type="primary", use_container_width=True):
                ud = cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (u, p)).fetchone()
                if ud:
                    st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]
                    tk = create_login_session(ud[0]); st.query_params["session"] = tk; st.rerun()
                else: st.error("Sai thông tin!")

        with t2:
            ca, cb = st.columns(2)
            with ca: ru = st.text_input("User ID", key="ru"); rn = st.text_input("Tên hiển thị", key="rn"); rp = st.text_input("SĐT", key="rp")
            with cb: rpass = st.text_input("Pass", type="password", key="rpa"); rr = st.radio("Role", ["Nhân viên", "Quản lý"], horizontal=True)
            rwp = "ADMIN"; key_m = ""
            if rr == "Nhân viên": rwp = st.text_input("Mã Chi Nhánh")
            elif rr == "Quản lý": key_m = st.text_input("Key Admin", type="password")
            
            if st.button("Đăng Ký", use_container_width=True):
                if not ru or not rpass or not rn: st.warning("Điền đủ thông tin!")
                else:
                    try:
                        if rr == "Nhân viên" and not cursor.execute("SELECT id FROM workplaces WHERE id=?", (rwp,)).fetchone(): st.error("Sai mã CN!"); st.stop()
                        if rr == "Quản lý":
                            if not cursor.execute("SELECT key_code FROM license_keys WHERE key_code=? AND status='active'", (key_m,)).fetchone(): st.error("Key sai!"); st.stop()
                            else: cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (key_m,))
                        
                        op = os.path.join(STORAGE_DIR, ru); 
                        if os.path.exists(op): shutil.rmtree(op)
                        cursor.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (ru, rpass, 'admin' if rr=="Quản lý" else 'staff', None, rn, rwp, rp, None, "2099-01-01"))
                        conn.commit(); st.success("OK! Đăng nhập đi."); 
                    except: st.error("User đã tồn tại.")

        with t3:
            su = st.text_input("Super User"); sp = st.text_input("Super Pass", type="password")
            if st.button("Login Super", use_container_width=True):
                if su == SUPER_ADMIN_USER and sp == SUPER_ADMIN_PASS: st.session_state.user="SUPER_ADMIN"; st.session_state.role="super_admin"; st.rerun()
                else: st.error("Sai!")
    st.stop()

# ==============================================================================
# 5. MAIN APP
# ==============================================================================
cu = st.session_state.user; cr = st.session_state.role; cz = st.session_state.zalo; cwp = st.session_state.wp_id

with st.sidebar:
    st.image(get_avatar_url(cz), width=100); st.title(cz); st.caption(f"ID: {cu} | {cr}")
    if cwp and cwp != "ADMIN": st.caption(f"Chi nhánh: {cwp}")
    st.divider()
    if st.button("🚪 Đăng xuất", use_container_width=True):
        if "session" in st.query_params: cursor.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],)); conn.commit(); st.query_params.clear()
        del st.session_state.user; st.rerun()

if cr == 'super_admin':
    st.header("🔧 SUPER ADMIN")
    t1, t2 = st.tabs(["Key", "Reset"])
    with t1:
        kt = st.selectbox("Loại Key", ["30 Ngày", "365 Ngày", "Vĩnh viễn"])
        if st.button("Sinh Key"): 
            k = str(uuid.uuid4())[:8].upper(); d = 36500 if kt == "Vĩnh viễn" else (365 if kt == "365 Ngày" else 30)
            cursor.execute("INSERT INTO license_keys VALUES (?,?,?)", (k, d, "active")); conn.commit(); st.success(f"Key: {k}")
        st.dataframe(pd.read_sql_query("SELECT * FROM license_keys", conn))
    with t2:
        if st.button("💣 RESET ALL"): 
            st.cache_resource.clear(); cursor.close(); conn.close()
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            if os.path.exists(STORAGE_DIR): shutil.rmtree(STORAGE_DIR); os.makedirs(STORAGE_DIR)
            if os.path.exists(UPLOAD_DIR): shutil.rmtree(UPLOAD_DIR); os.makedirs(UPLOAD_DIR)
            st.success("Đã Reset!"); st.stop()
    st.stop()

if cr == 'admin':
    dl = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if dl < 0:
        st.error(f"🔒 Hết hạn!"); k = st.text_input("Key:")
        if st.button("Kích hoạt"):
            kd = cursor.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (k,)).fetchone()
            if kd:
                n = (datetime.now() + timedelta(days=kd[0])).strftime("%Y-%m-%d")
                cursor.execute("UPDATE users SET expiry_date=? WHERE username=?", (n, cu)); cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (k,)); conn.commit(); st.session_state.expiry=n; st.success("OK!"); time.sleep(1); st.rerun()
            else: st.error("Lỗi Key.")
        st.stop()

tc, tw = st.tabs(["💬 Chat", "📊 Công Việc"])

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
        render_chat_window(aroom, cz, "group" if cmode == "🏢 Nhóm Chung" else "private")
        c1, c2 = st.columns([6, 1])
        with c1:
            mi = st.chat_input("Nhập tin nhắn...")
            if mi: cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", (aroom, cz, mi, datetime.now().strftime("%H:%M"), "text")); conn.commit()
        with c2:
            with st.popover("➕", use_container_width=True):
                if st.button("📹 Call", use_container_width=True): lk = f"https://meet.jit.si/v_{uuid.uuid4()}"; cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (aroom, cz, f"v|{lk}", datetime.now().strftime("%H:%M"), "call")); conn.commit(); st.rerun()
                up = st.file_uploader("", type=['png','jpg'], label_visibility="collapsed")
                if up and st.button("Gửi Ảnh", use_container_width=True):
                    e = up.name.split('.')[-1]; f = f"{uuid.uuid4()}.{e}"; p = os.path.join(UPLOAD_DIR, f)
                    with open(p, "wb") as x: x.write(up.getbuffer())
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (aroom, cz, p, datetime.now().strftime("%H:%M"), "image")); conn.commit(); st.rerun()

with tw:
    if cr == 'admin':
        with st.expander("⚙️ CẤU HÌNH"):
            c1, c2 = st.columns(2)
            with c1: ni = st.text_input("Mã ID").upper()
            with c2: nn = st.text_input("Tên CN")
            if st.button("Tạo"): 
                try: cursor.execute("INSERT INTO workplaces VALUES (?,?,?)", (ni, nn, cu)); conn.commit(); st.success("OK"); st.rerun()
                except: st.error("Trùng mã")
        
        sl = cursor.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        render_dashboard(sl)
        
        if sl:
            st.divider(); sel = st.selectbox("📝 Quản lý:", [f"{s[1]} ({s[0]})" for s in sl]); tid = sel.split('(')[1].replace(')', '')
            tf = os.path.join(STORAGE_DIR, tid, "salary.xlsx"); dfs = load_excel_safe(tf)
            
            prows = len(dfs[dfs["Xác nhận đến"].astype(str).str.lower() == "false"])
            cdebt = pd.to_numeric(dfs[dfs["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
            
            st.info(f"SĐT: {sl[[s[0] for s in sl].index(tid)][3]}")
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Nợ:", f"{cdebt:,.0f}")
            with c2: st.metric("Chờ duyệt:", f"{prows}")
            with c3:
                if prows > 0 and st.button("✅ DUYỆT TẤT CẢ", use_container_width=True):
                    dfs.loc[dfs["Xác nhận đến"].astype(str).str.lower() == "false", "Xác nhận đến"] = True; save_excel_safe(dfs, tf); st.success("Done!"); time.sleep(1); st.rerun()
                if cdebt > 0 and st.button("💸 Thanh Toán", use_container_width=True):
                    dfs.loc[dfs["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False), "Trạng thái"] = "nhận"; save_excel_safe(dfs, tf)
                    twp = [s[2] for s in sl if s[0] == tid][0]
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (twp, cz, f"✅ Đã trả: {cdebt:,.0f}", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.rerun()
            
            with st.expander("➕ Thêm Ca"):
                with st.form("aa"):
                    d = st.date_input("Ngày"); v = st.text_input("VT", "Tại quán"); t1 = st.time_input("Vào"); t2 = st.time_input("Ra"); r = st.number_input("Lương", 20000)
                    if st.form_submit_button("Lưu"):
                        dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                        if dt2 < dt1: dt2 += timedelta(days=1)
                        h = (dt2 - dt1).total_seconds() / 3600
                        new = pd.DataFrame([{"Ngày": d.strftime("%Y-%m-%d"), "Vị trí": v, "Giờ vào": t1.strftime("%H:%M"), "Giờ ra": t2.strftime("%H:%M"), "Tổng lương": h*r, "Trạng thái": "chưa nhận", "Xác nhận đến": True}])
                        dfs = pd.concat([dfs, new], ignore_index=True); save_excel_safe(dfs, tf); st.success("OK"); st.rerun()
            st.dataframe(dfs, use_container_width=True)

    elif cr == 'staff':
        mf = os.path.join(STORAGE_DIR, cu, "salary.xlsx"); dfm = load_excel_safe(mf)
        md = pd.to_numeric(dfm[dfm["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
        mp = len(dfm[dfm["Xác nhận đến"].astype(str).str.lower() == "false"]) if "Xác nhận đến" in dfm.columns else 0

        c1, c2 = st.columns(2)
        with c1: st.metric("💰 Nợ bạn:", f"{md:,.0f}")
        with c2: st.metric("⏳ Chờ duyệt:", f"{mp}")
        
        if md > 0 and st.button("🔔 Đòi tiền", use_container_width=True): cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (cwp, cz, f"📣 Check lương: {md:,.0f}", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.toast("Đã gửi!")
        
        with st.expander("➕ Báo cáo ca", expanded=True):
            with st.form("sa"):
                d = st.date_input("Ngày"); v = st.text_input("VT", cwp); t1 = st.time_input("Vào"); t2 = st.time_input("Ra"); sr = st.number_input("Lương", 20000)
                if st.form_submit_button("Lưu"):
                    dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                    if dt2 < dt1: dt2 += timedelta(days=1)
                    h = (dt2 - dt1).total_seconds() / 3600
                    new = pd.DataFrame([{"Ngày": d.strftime("%Y-%m-%d"), "Vị trí": v, "Giờ vào": t1.strftime("%H:%M"), "Giờ ra": t2.strftime("%H:%M"), "Tổng lương": h*sr, "Trạng thái": "chưa nhận", "Xác nhận đến": False}])
                    dfm = pd.concat([dfm, new], ignore_index=True); save_excel_safe(dfm, mf); st.success("Lưu thành công!"); st.rerun()
        st.dataframe(dfm, use_container_width=True)