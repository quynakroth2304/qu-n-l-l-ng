import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
from datetime import datetime, timedelta

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
st.set_page_config(page_title="Hệ Thống V24 (Call Video)", layout="wide", page_icon="📹")

DB_FILE = "system_v24_pro.db" 
STORAGE = "user_files"
IMG_FOLDER = "chat_uploads"

if not os.path.exists(STORAGE): os.makedirs(STORAGE)
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

# --- KẾT NỐI DATABASE ---
@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# --- KHỞI TẠO BẢNG ---
def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
                  qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT,
                  license_key TEXT, expiry_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS workplaces
                 (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS license_keys
                 (key_code TEXT PRIMARY KEY, duration_days INTEGER, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, workplace_id TEXT, 
                  sender TEXT, content TEXT, timestamp TEXT, msg_type TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (token TEXT PRIMARY KEY, username TEXT, expiry TEXT)''')
    conn.commit()

init_db()

# --- SUPER ADMIN ---
SUPER_ADMIN_USER = "admin"
SUPER_ADMIN_PASS = "19051976"

# ==========================================
# 2. CÁC HÀM HỖ TRỢ
# ==========================================
def find_col(df, keywords):
    if isinstance(keywords, str): keywords = [keywords]
    for col in df.columns:
        for key in keywords:
            if key.lower() in str(col).lower(): return col
    return None

def load_excel_safe(path):
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"])
    try: return pd.read_excel(path)
    except: return pd.DataFrame()

# --- AUTO LOGIN ---
def create_session(username):
    token = str(uuid.uuid4())
    exp = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, exp))
    conn.commit()
    return token

def get_user_from_session(token):
    try:
        c.execute("SELECT username, expiry FROM sessions WHERE token=?", (token,))
        row = c.fetchone()
        if row and datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S") > datetime.now(): return row[0]
    except: pass
    return None

if "session" in st.query_params:
    auto_user = get_user_from_session(st.query_params["session"])
    if auto_user and 'user' not in st.session_state:
        c.execute('SELECT * FROM users WHERE username=?', (auto_user,))
        ud = c.fetchone()
        if ud:
            st.session_state.user = ud[0]; st.session_state.role = ud[2]; st.session_state.zalo = ud[4]
            st.session_state.wp_id = ud[5]; st.session_state.expiry = ud[8]

# ==========================================
# 3. GIAO DIỆN CHAT (REAL-TIME 1S)
# ==========================================
@st.fragment(run_every=2)
def render_chat_box(room_id, current_user_zalo, chat_type="group"):
    try:
        c.execute("SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,))
        msgs = c.fetchall()[::-1]
    except: return

    # Tiêu đề khung chat
    title_icon = "🏢" if chat_type == "group" else "🔒"
    title_text = f"Nhóm: {room_id}" if chat_type == "group" else f"Chat riêng: {room_id.replace('DM_', '').replace(current_user_zalo, '').replace('_', '')}"
    st.caption(f"{title_icon} **{title_text}** (Cập nhật 2s/lần)")
    
    st.markdown("""<style>.tagged { background-color: #ffe6e6; border: 2px solid #ff4d4d; padding: 10px; border-radius: 10px; color: #b30000; font-weight: bold; margin-bottom: 5px;} .call-box {background-color: #e3f2fd; border: 1px solid #2196f3; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 5px;}</style>""", unsafe_allow_html=True)

    with st.container(height=450):
        if not msgs: st.info("👋 Bắt đầu cuộc trò chuyện mới!")
        for sender, content, ts, m_type in msgs:
            is_me = (sender == current_user_zalo)
            is_tagged = (m_type == 'text' and content and f"@{current_user_zalo}" in content)
            
            with st.chat_message("user" if is_me else "assistant", avatar="👤" if is_me else "🤖"):
                st.caption(f"{sender} • {ts}")
                
                if m_type == 'image':
                    if os.path.exists(content): st.image(content, width=250)
                elif m_type == 'emoji': st.markdown(f"## {content}")
                elif m_type == 'call':
                    # Hiển thị nút tham gia cuộc gọi
                    call_type = "📹 Video Call" if "video" in content else "📞 Voice Call"
                    link = content.split('|')[-1]
                    st.markdown(f"""
                    <div class="call-box">
                        <b>{sender} đang gọi...</b><br>
                        <a href="{link}" target="_blank" style="text-decoration: none;">
                            <button style="background-color: #4CAF50; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin-top: 5px;">
                                👉 Bấm để tham gia {call_type}
                            </button>
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if is_tagged: st.markdown(f'<div class="tagged">🔔 @{current_user_zalo}, bạn được nhắc:<br>{content}</div>', unsafe_allow_html=True)
                    else: st.write(content)

# ==========================================
# 4. ĐĂNG NHẬP / ĐĂNG KÝ
# ==========================================
if 'user' not in st.session_state:
    st.title("🔐 Hệ Thống V24 (Call Video)")
    t_log, t_reg, t_super = st.tabs(["Đăng nhập", "Đăng ký", "Super Admin"])
    
    with t_super:
        sa_u = st.text_input("User"); sa_p = st.text_input("Pass", type="password")
        if st.button("Login Super"):
            if sa_u == SUPER_ADMIN_USER and sa_p == SUPER_ADMIN_PASS:
                st.session_state.user = "SUPER_ADMIN"; st.session_state.role = "super_admin"; st.rerun()

    with t_reg:
        st.info("⚠️ Hệ thống nâng cấp. Vui lòng đăng ký mới nếu chưa có tài khoản.")
        c1, c2 = st.columns(2)
        with c1: u_r = st.text_input("User ID", key="r_u"); z_r = st.text_input("Zalo Name", key="r_z"); p_r = st.text_input("Phone", key="r_p")
        with c2: pass_r = st.text_input("Pass", type="password", key="r_pa"); r_r = st.radio("Role", ["Nhân viên", "Quản lý"], horizontal=True)
        wp_in = st.text_input("Mã Chi Nhánh (Nếu là NV)", key="r_w") if r_r == "Nhân viên" else "ADMIN"
        
        if st.button("Đăng ký"):
            try:
                if r_r == "Nhân viên":
                    c.execute("SELECT id FROM workplaces WHERE id=?", (wp_in,))
                    if not c.fetchone(): st.error("Mã chi nhánh không tồn tại!"); st.stop()
                c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (u_r, pass_r, 'admin' if r_r=="Quản lý" else 'staff', None, z_r, wp_in, p_r, None, "2000-01-01"))
                conn.commit(); st.success("Đăng ký thành công!"); 
            except: st.error("ID đã tồn tại.")

    with t_log:
        u_l = st.text_input("User ID", key="l_u"); p_l = st.text_input("Pass", type="password", key="l_p")
        if st.button("Đăng nhập"):
            c.execute('SELECT * FROM users WHERE username=? AND password=?', (u_l, p_l))
            ud = c.fetchone()
            if ud:
                st.session_state.user = ud[0]; st.session_state.role = ud[2]; st.session_state.zalo = ud[4]
                st.session_state.wp_id = ud[5]; st.session_state.expiry = ud[8]
                token = create_session(ud[0]); st.query_params["session"] = token
                st.rerun()
            else: st.error("Sai thông tin!")
    st.stop()

# --- SAU KHI LOGIN ---
user = st.session_state.user; role = st.session_state.role
zalo = st.session_state.zalo if 'zalo' in st.session_state else user
wp_id = st.session_state.wp_id if 'wp_id' in st.session_state else ""

with st.sidebar:
    st.title(f"👋 {zalo}"); st.caption(f"Role: {role}")
    if st.button("Đăng xuất"):
        if "session" in st.query_params: c.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],)); conn.commit(); st.query_params.clear()
        del st.session_state.user; st.rerun()

# --- SUPER ADMIN ---
if role == 'super_admin':
    st.header("🔑 SUPER ADMIN"); k_t = st.selectbox("Key", [30, 365]); 
    if st.button("Sinh Key"): k = str(uuid.uuid4())[:8].upper(); c.execute("INSERT INTO license_keys VALUES (?,?,?)", (k, k_t, "active")); conn.commit(); st.success(f"Key: {k}")
    if st.button("RESET TOÀN BỘ"): st.cache_resource.clear(); c.close(); conn.close(); os.remove(DB_FILE); st.success("Đã xóa DB!"); time.sleep(1); st.rerun()
    st.stop()

# --- CHECK LICENSE ---
if role == 'admin':
    days = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if days < 0:
        st.error(f"🔒 Hết hạn!"); k_in = st.text_input("Nhập Key:"); 
        if st.button("Kích hoạt"):
            d = c.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (k_in,)).fetchone()
            if d:
                nex = (datetime.now()+timedelta(days=d[0])).strftime("%Y-%m-%d"); c.execute("UPDATE users SET expiry_date=? WHERE username=?", (nex, user)); c.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (k_in,)); conn.commit(); st.session_state.expiry = nex; st.rerun()
            else: st.error("Lỗi Key!")
        st.stop()

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
tab_chat, tab_work = st.tabs(["💬 Trung Tâm Liên Lạc", "📊 Quản Lý Công Việc"])

# --- TAB 1: CHAT & CALL ---
with tab_chat:
    # 1. CHỌN CHẾ ĐỘ CHAT
    chat_mode = st.radio("Chế độ:", ["🏢 Nhóm Chung", "👤 Nhắn Riêng"], horizontal=True, label_visibility="collapsed")
    
    active_room = None
    
    if chat_mode == "🏢 Nhóm Chung":
        if role == 'admin':
            rooms = [r[0] for r in c.execute("SELECT id FROM workplaces").fetchall()]
            if rooms: active_room = st.selectbox("Chọn nhóm:", rooms)
            else: st.warning("Chưa có nhóm nào!")
        else:
            active_room = wp_id # Nhân viên chỉ thấy nhóm mình
            
    else: # Nhắn Riêng
        # Lấy danh sách user khác mình
        users = c.execute("SELECT zalo_name FROM users WHERE username != ?", (user,)).fetchall()
        user_list = [u[0] for u in users]
        if user_list:
            target_user = st.selectbox("Chọn người nhắn:", user_list)
            # Tạo Room ID duy nhất cho 2 người (Sắp xếp tên để A nhắn B giống B nhắn A)
            pair = sorted([zalo, target_user])
            active_room = f"DM_{pair[0]}_{pair[1]}"
        else:
            st.info("Chưa có ai để nhắn.")

    # 2. HIỂN THỊ KHUNG CHAT & CÔNG CỤ
    if active_room:
        render_chat_box(active_room, zalo, "private" if chat_mode == "👤 Nhắn Riêng" else "group")
        
        c1, c2 = st.columns([5, 1])
        with c1:
            if p := st.chat_input("Nhập tin nhắn..."):
                c.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", (active_room, zalo, p, datetime.now().strftime("%H:%M"), "text")); conn.commit()
        
        with c2:
            with st.popover("➕ Tiện ích"):
                st.write("**Gọi điện:**")
                cc1, cc2 = st.columns(2)
                
                # Nút Gọi Thoại
                if cc1.button("📞 Voice"):
                    # Tạo link Jitsi ngẫu nhiên
                    call_id = f"voice_{uuid.uuid4()}"
                    link = f"https://meet.jit.si/{call_id}#config.startWithVideoMuted=true"
                    msg = f"voice|{link}"
                    c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, msg, datetime.now().strftime("%H:%M"), "call")); conn.commit(); st.rerun()
                
                # Nút Gọi Video
                if cc2.button("📹 Video"):
                    call_id = f"video_{uuid.uuid4()}"
                    link = f"https://meet.jit.si/{call_id}"
                    msg = f"video|{link}"
                    c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, msg, datetime.now().strftime("%H:%M"), "call")); conn.commit(); st.rerun()

                st.divider()
                st.write("**Gửi ảnh/Icon:**")
                ec = st.columns(4)
                for i,e in enumerate(["👍","❤️","😂","OK"]): 
                    if ec[i].button(e): c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, e, datetime.now().strftime("%H:%M"), "emoji")); conn.commit(); st.rerun()
                
                img = st.file_uploader("", type=['png','jpg'], key="img_up")
                if img and st.button("Gửi Ảnh"):
                    ext = img.name.split('.')[-1]; fname = f"{uuid.uuid4()}.{ext}"; fpath = os.path.join(IMG_FOLDER, fname)
                    with open(fpath, "wb") as f: f.write(img.getbuffer())
                    c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, fpath, datetime.now().strftime("%H:%M"), "image")); conn.commit(); st.rerun()

# --- TAB 2: QUẢN LÝ ---
with tab_work:
    if role == 'admin':
        with st.expander("🏢 CẤU HÌNH"):
            ni = st.text_input("Mã ID").upper(); nn = st.text_input("Tên")
            if st.button("Tạo"): 
                try: c.execute("INSERT INTO workplaces VALUES (?,?,?)", (ni, nn, user)); conn.commit(); st.success(f"Tạo {ni}"); st.rerun()
                except: st.error("Trùng!")
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