import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
from datetime import datetime, timedelta

# ==========================================
# 1. CẤU HÌNH & CSS FACEBOOK MESSENGER
# ==========================================
st.set_page_config(page_title="Hệ Thống V26 Messenger", layout="wide", page_icon="💬")

# CSS CHUẨN FACEBOOK (Tinh chỉnh từng pixel)
st.markdown("""
<style>
    /* Ẩn padding thừa của Streamlit */
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    
    /* Container khung chat */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 2px; /* Khoảng cách giữa các tin cực nhỏ giống FB */
        padding: 10px;
        overflow-y: auto;
        max-height: 70vh; /* Giới hạn chiều cao để scroll */
    }

    /* Hàng tin nhắn (Row) */
    .msg-row {
        display: flex;
        align-items: flex-end; /* Avatar nằm dưới cùng */
        margin-bottom: 5px;
    }

    /* 1. Tin nhắn của NGƯỜI KHÁC (Bên Trái) */
    .msg-left {
        justify-content: flex-start;
    }
    .msg-left .avatar {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        margin-right: 8px;
        background-color: #ddd;
        border: 1px solid #eee;
        object-fit: cover;
    }
    .msg-left .bubble {
        background-color: #e4e6eb; /* Màu xám FB */
        color: #050505;
        padding: 8px 12px;
        border-radius: 18px;
        font-size: 15px;
        max-width: 70%;
        position: relative;
        font-family: Helvetica, Arial, sans-serif;
    }

    /* 2. Tin nhắn của TÔI (Bên Phải) */
    .msg-right {
        justify-content: flex-end;
    }
    .msg-right .bubble {
        background-color: #0084ff; /* Màu xanh FB */
        color: white;
        padding: 8px 12px;
        border-radius: 18px;
        font-size: 15px;
        max-width: 70%;
        font-family: Helvetica, Arial, sans-serif;
    }
    /* Ẩn avatar của chính mình cho gọn (giống FB) */
    .msg-right .avatar { display: none; }

    /* Hiển thị Tên người gửi nhỏ xíu trên đầu tin nhắn nhóm */
    .sender-name {
        font-size: 11px;
        color: #65676b;
        margin-left: 46px; /* Canh lề cho thẳng với bubble */
        margin-bottom: 2px;
        margin-top: 4px;
    }

    /* Hình ảnh trong chat */
    .chat-img {
        border-radius: 12px;
        max-width: 250px;
        border: 1px solid #ddd;
    }

    /* Sticker/Emoji to */
    .emoji-big { font-size: 40px; }

    /* Nút gọi Video đẹp */
    .call-card {
        background: white;
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 10px;
        display: flex;
        align-items: center;
        gap: 10px;
        width: fit-content;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .call-btn {
        background-color: #00c853;
        color: white;
        border: none;
        padding: 6px 15px;
        border-radius: 20px;
        font-weight: bold;
        text-decoration: none;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE & LOGIC
# ==========================================
DB_FILE = "system_v26_fb.db" 
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
# 3. ENGINE HIỂN THỊ CHAT (CUSTOM HTML)
# ==========================================
# Hàm tạo URL Avatar ngẫu nhiên theo tên (Giống Gmail)
def get_avatar_url(name):
    return f"https://ui-avatars.com/api/?name={name}&background=random&color=fff&size=64"

# Hàm chuyển ảnh local thành base64 để hiển thị trong HTML (nếu cần) 
# Nhưng ở đây ta dùng đường dẫn tương đối hoặc hiển thị trực tiếp bằng st.image ngoài HTML cho đơn giản
# Tuy nhiên để nhúng vào HTML custom, ta dùng thẻ img trỏ tới file
# Streamlit hosting file local hơi phức tạp, nên ta dùng cách hiển thị kết hợp.

@st.fragment(run_every=2)
def render_chat_fb_style(room_id, current_user_zalo, chat_type="group"):
    try:
        # Lấy tin nhắn cũ nhất lên trước (để chat xuôi dòng từ trên xuống dưới)
        # Sửa: Lấy 50 tin mới nhất, sau đó đảo ngược để hiển thị đúng thứ tự thời gian
        msgs = c.execute("SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,)).fetchall()[::-1]
    except: return

    # Header
    icon = "🏢" if chat_type == "group" else "💬"
    room_name = room_id if chat_type == "group" else room_id.replace("DM_", "").replace(current_user_zalo, "").replace("_", "")
    st.markdown(f"#### {icon} {room_name}")

    # Xây dựng chuỗi HTML khổng lồ
    html_content = '<div class="chat-container">'
    
    last_sender = None
    
    for sender, content, ts, m_type in msgs:
        is_me = (sender == current_user_zalo)
        align_class = "msg-right" if is_me else "msg-left"
        
        # Chỉ hiện tên người gửi nếu là tin nhắn nhóm và người gửi khác mình và khác tin trước
        show_name = (chat_type == "group" and not is_me and sender != last_sender)
        if show_name:
            html_content += f'<div class="sender-name">{sender} • {ts}</div>'
        
        # Bắt đầu hàng tin nhắn
        html_content += f'<div class="msg-row {align_class}">'
        
        # Avatar (chỉ hiện cho người khác)
        if not is_me:
             html_content += f'<img src="{get_avatar_url(sender)}" class="avatar">'
        
        # Nội dung Bubble
        if m_type == 'image':
            # Với ảnh, ta dùng st.image của Streamlit thì tốt hơn, nhưng không nhúng được vào div custom.
            # Giải pháp: Dùng thẻ img với base64 hoặc đường dẫn. 
            # Để đơn giản và nhanh, ta hiển thị text placeholder trong HTML và render ảnh ra ngoài? Không được vì vỡ layout.
            # Ta sẽ dùng Base64 để nhúng ảnh trực tiếp vào HTML.
            if os.path.exists(content):
                import base64
                with open(content, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                html_content += f'<img src="data:image/png;base64,{b64}" class="chat-img">'
            else:
                html_content += '<div class="bubble">⚠️ Ảnh lỗi</div>'
                
        elif m_type == 'emoji':
            html_content += f'<div class="emoji-big">{content}</div>'
            
        elif m_type == 'call':
            link = content.split('|')[-1]
            icon_call = "📹" if "video" in content else "📞"
            html_content += f'''
            <div class="call-card">
                <div style="font-size:20px">{icon_call}</div>
                <div>
                    <div style="font-weight:bold; font-size:12px; color:#333">{sender} đang gọi...</div>
                    <a href="{link}" target="_blank" class="call-btn">Tham gia</a>
                </div>
            </div>
            '''
            
        else: # Text thường
            # Xử lý Tag tên
            if f"@{current_user_zalo}" in content:
                 content = f"<span style='background:#fff3cd; color:#856404; padding:2px 4px; border-radius:4px; font-weight:bold'>{content}</span>"
            
            html_content += f'<div class="bubble" title="{ts}">{content}</div>'
        
        html_content += '</div>' # End row
        last_sender = sender

    html_content += '</div>' # End container
    
    # Render HTML
    st.markdown(html_content, unsafe_allow_html=True)
    
    # Javascript để tự cuộn xuống đáy (Auto Scroll)
    st.markdown("""
        <script>
            var element = window.parent.document.querySelector('.chat-container');
            if (element) { element.scrollTop = element.scrollHeight; }
        </script>
    """, unsafe_allow_html=True)


# ==========================================
# 4. GIAO DIỆN CHÍNH
# ==========================================
# ... (Phần Login/Register giữ nguyên logic V25 cho gọn, chỉ thay đổi phần Chat) ...

if 'user' not in st.session_state:
    st.title("🔐 Login V26 Messenger")
    t1, t2 = st.tabs(["Đăng nhập", "Đăng ký"])
    with t1:
        u = st.text_input("User"); p = st.text_input("Pass", type="password")
        if st.button("Login"):
            ud = c.execute('SELECT * FROM users WHERE username=? AND password=?', (u, p)).fetchone()
            if ud:
                 st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]
                 token = create_session(ud[0]); st.query_params["session"] = token; st.rerun()
            else: st.error("Sai!")
    with t2:
        c1, c2 = st.columns(2)
        with c1: u_r = st.text_input("User", key="r1"); z_r = st.text_input("Zalo", key="r2"); p_r = st.text_input("Phone", key="r3")
        with c2: p_rr = st.text_input("Pass", type="password", key="r4"); r_r = st.radio("Role", ["Nhân viên", "Quản lý"])
        wp = st.text_input("Mã Chi Nhánh") if r_r == "Nhân viên" else "ADMIN"
        if st.button("Đăng ký"):
            try:
                if r_r=="Nhân viên" and not c.execute("SELECT id FROM workplaces WHERE id=?", (wp,)).fetchone(): st.error("Sai mã CN!"); st.stop()
                c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (u_r, p_rr, 'admin' if r_r=="Quản lý" else 'staff', None, z_r, wp, p_r, None, "2000-01-01")); conn.commit(); st.success("OK")
            except: st.error("Trùng ID")
    st.stop()

# --- APP ---
user = st.session_state.user; role = st.session_state.role; zalo = st.session_state.zalo; wp_id = st.session_state.wp_id

with st.sidebar:
    st.image(get_avatar_url(zalo), width=80)
    st.title(zalo); st.caption(f"ID: {user} | {role}")
    if st.button("Đăng xuất"): 
        if "session" in st.query_params: c.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],)); conn.commit(); st.query_params.clear()
        del st.session_state.user; st.rerun()

# --- ADMIN CHECK LICENSE ---
if role == 'admin':
    days = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if days < 0:
        st.error(f"Hết hạn!"); k = st.text_input("Key:"); 
        if st.button("Kích hoạt"):
            d = c.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (k,)).fetchone()
            if d: nex=(datetime.now()+timedelta(days=d[0])).strftime("%Y-%m-%d"); c.execute("UPDATE users SET expiry_date=? WHERE username=?", (nex, user)); c.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (k,)); conn.commit(); st.session_state.expiry=nex; st.rerun()
            else: st.error("Lỗi")
        st.stop()

# --- TABS ---
t_chat, t_work, t_super = st.tabs(["💬 Messenger", "📊 Công Việc", "🔧 Super Admin"])

with t_chat:
    mode = st.radio("Chế độ:", ["🏢 Nhóm", "👤 Riêng"], horizontal=True, label_visibility="collapsed")
    active_room = None
    if mode == "🏢 Nhóm":
        if role == 'admin': 
            rms = [r[0] for r in c.execute("SELECT id FROM workplaces").fetchall()]
            active_room = st.selectbox("Chọn:", rms) if rms else None
        else: active_room = wp_id
    else:
        us = [u[0] for u in c.execute("SELECT zalo_name FROM users WHERE username != ?", (user,)).fetchall()]
        if us: target = st.selectbox("Người:", us); active_room = f"DM_{sorted([zalo, target])[0]}_{sorted([zalo, target])[1]}"
    
    if active_room:
        # RENDER CHAT FACEBOOK STYLE
        render_chat_fb_style(active_room, zalo, "group" if mode=="🏢 Nhóm" else "private")
        
        # INPUT AREA
        c1, c2 = st.columns([6, 1])
        with c1:
            if p := st.chat_input("Nhập tin nhắn..."):
                c.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", (active_room, zalo, p, datetime.now().strftime("%H:%M"), "text")); conn.commit()
        with c2:
            with st.popover("➕"):
                if st.button("📹 Video"): link=f"https://meet.jit.si/v_{uuid.uuid4()}"; c.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (active_room, zalo, f"v|{link}", datetime.now().strftime("%H:%M"), "call")); conn.commit(); st.rerun()
                ec = st.columns(4)
                for i,e in enumerate(["👍","❤️","😂","OK"]): 
                    if ec[i].button(e): c.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (active_room, zalo, e, datetime.now().strftime("%H:%M"), "emoji")); conn.commit(); st.rerun()
                img = st.file_uploader("", type=['png','jpg'], label_visibility="collapsed")
                if img and st.button("Gửi"):
                    ext = img.name.split('.')[-1]; fname = f"{uuid.uuid4()}.{ext}"; fpath = os.path.join(IMG_FOLDER, fname); 
                    with open(fpath, "wb") as f: f.write(img.getbuffer())
                    c.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (active_room, zalo, fpath, datetime.now().strftime("%H:%M"), "image")); conn.commit(); st.rerun()

with t_work:
    if role == 'admin':
        with st.expander("🏢 CẤU HÌNH"):
            ni = st.text_input("Mã ID").upper(); nn = st.text_input("Tên")
            if st.button("Tạo"): 
                try: c.execute("INSERT INTO workplaces VALUES (?,?,?)", (ni, nn, user)); conn.commit(); st.success("OK"); st.rerun()
                except: st.error("Trùng")
            st.dataframe(pd.DataFrame(c.execute("SELECT id, name FROM workplaces").fetchall(), columns=["ID", "Name"]))
        
        staffs = c.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        if staffs:
            sel = st.selectbox("Chọn NV", [f"{s[1]} ({s[0]})" for s in staffs]); uid = sel.split("(")[1].replace(")","")
            p_path = os.path.join(STORAGE, uid, "salary.xlsx"); df = load_excel_safe(p_path)
            c_tt = find_col(df, "trạng thái"); c_tl = find_col(df, "tổng"); debt = pd.to_numeric(df[df[c_tt].astype(str).str.lower().str.contains("chưa", na=False)][c_tl], errors='coerce').sum() if c_tt else 0
            
            st.write(f"**Nợ: {debt:,.0f} VNĐ**")
            if debt > 0 and st.button("Thanh toán"):
                df.loc[df[c_tt].astype(str).str.lower().str.contains("chưa", na=False), c_tt] = "nhận"; df.to_excel(p_path, index=False)
                c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", ([s[2] for s in staffs if s[0]==uid][0], zalo, f"✅ Đã trả {debt:,.0f}", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.rerun()
            
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
        st.metric("Nợ bạn", f"{due:,.0f} VNĐ")
        if due > 0 and st.button("Đòi tiền"): c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (wp_id, zalo, f"📣 Trả {due:,.0f} đi!", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.toast("Đã gửi!")
        
        with st.form("s"):
            d=st.date_input("Ngày"); v=st.text_input("VT", wp_id); t1=st.time_input("In"); t2=st.time_input("Out")
            if st.form_submit_button("Lưu"):
                s=datetime.combine(d,t1); e=datetime.combine(d,t2); 
                if e<s: e+=timedelta(days=1)
                pd.concat([df, pd.DataFrame([{find_col(df,"ngày"):"%s"%d, find_col(df,"vị trí"):v, find_col(df,"tổng"):(e-s).seconds/3600*20000, "Trạng thái":"chưa nhận", find_col(df,"vào"):"%s"%t1, find_col(df,"ra"):"%s"%t2, "Xác nhận đến":False}])], ignore_index=True).to_excel(f, index=False); st.rerun()
        st.dataframe(df)

if role == 'super_admin':
    st.header("🔑 SUPER ADMIN")
    if st.button("Sinh Key"): k = str(uuid.uuid4())[:8].upper(); c.execute("INSERT INTO license_keys VALUES (?,?,?)", (k, 365, "active")); conn.commit(); st.success(k)
    if st.button("Reset DB"): st.cache_resource.clear(); c.close(); conn.close(); os.remove(DB_FILE); st.success("Xong"); st.rerun()