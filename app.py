import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
import shutil
from datetime import datetime, timedelta

# ==========================================
# 🛑 KHU VỰC DỌN DẸP DỮ LIỆU CŨ (FIX LỖI)
# ==========================================
# Danh sách các file DB cũ cần tiêu hủy
old_dbs = [
    "system_v20_full.db", "system_v19_test.db", "system_v18_new.db", 
    "system_v17_reset.db", "system_v15_fixed.db", "system_v15_final.db"
]

# Chỉ chạy dọn dẹp 1 lần khi khởi động lại server
if "cleaned_once" not in st.session_state:
    st.cache_resource.clear() # Xóa cache kết nối cũ
    for db in old_dbs:
        if os.path.exists(db):
            try:
                os.remove(db)
                print(f"❌ Đã xóa file cũ: {db}")
            except: pass
    st.session_state.cleaned_once = True

# ==========================================
# CẤU HÌNH HỆ THỐNG MỚI (V21)
# ==========================================
DB_FILE = "system_v21_ultra_clean.db" # Database mới tinh
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
SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

st.set_page_config(page_title="Hệ Thống V21 (Sạch Sẽ)", layout="wide", page_icon="✨")

# --- HÀM HỖ TRỢ ---
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
        if row and datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S") > datetime.now():
            return row[0]
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
# PHẦN GIAO DIỆN CHAT (REAL-TIME 1S)
# ==========================================
@st.fragment(run_every=1)
def render_chat_box(room_id, current_user_zalo):
    try:
        c.execute("SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,))
        msgs = c.fetchall()[::-1]
    except: return

    st.caption(f"⚡ Phòng Chat: **{room_id}** (Cập nhật 1s)")
    st.markdown("""<style>.tagged { background-color: #ffe6e6; border: 2px solid #ff4d4d; padding: 10px; border-radius: 10px; color: #b30000; font-weight: bold; margin-bottom: 5px;}</style>""", unsafe_allow_html=True)

    with st.container(height=450):
        if not msgs: st.info("👋 Nhóm mới tinh, chưa có tin nhắn!")
        for sender, content, ts, m_type in msgs:
            is_me = (sender == current_user_zalo)
            is_tagged = (m_type == 'text' and content and f"@{current_user_zalo}" in content)
            with st.chat_message("user" if is_me else "assistant", avatar="👤" if is_me else "🤖"):
                st.caption(f"{sender} • {ts}")
                if m_type == 'image':
                    if os.path.exists(content): st.image(content, width=250)
                elif m_type == 'emoji': st.markdown(f"## {content}") 
                else:
                    if is_tagged: st.markdown(f'<div class="tagged">🔔 @{current_user_zalo}, bạn được nhắc:<br>{content}</div>', unsafe_allow_html=True)
                    else: st.write(content)

# ==========================================
# PHẦN ĐĂNG NHẬP / ĐĂNG KÝ
# ==========================================
if 'user' not in st.session_state:
    st.title("🔐 Hệ Thống V21 (Sạch Sẽ)")
    t_log, t_reg, t_super = st.tabs(["Đăng nhập", "Đăng ký", "Super Admin"])
    
    with t_super:
        sa_u = st.text_input("User"); sa_p = st.text_input("Pass", type="password")
        if st.button("Login Super"):
            if sa_u == SUPER_ADMIN_USER and sa_p == SUPER_ADMIN_PASS:
                st.session_state.user = "SUPER_ADMIN"; st.session_state.role = "super_admin"; st.rerun()

    with t_reg:
        st.info("⚠️ Hệ thống đã được dọn dẹp. Hãy tạo tài khoản mới.")
        c1, c2 = st.columns(2)
        with c1: u_r = st.text_input("User ID", key="r_u"); z_r = st.text_input("Zalo Name", key="r_z"); p_r = st.text_input("Phone", key="r_p")
        with c2: pass_r = st.text_input("Pass", type="password", key="r_pa"); r_r = st.radio("Role", ["Nhân viên", "Quản lý"], horizontal=True)
        wp_in = st.text_input("Mã Chi Nhánh (Nếu là NV)", key="r_w") if r_r == "Nhân viên" else "ADMIN"
        
        if st.button("Đăng ký"):
            try:
                if r_r == "Nhân viên":
                    c.execute("SELECT id FROM workplaces WHERE id=?", (wp_in,))
                    if not c.fetchone(): st.error("Mã chi nhánh chưa tồn tại (Quản lý cần tạo trước)!"); st.stop()
                
                c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (u_r, pass_r, 'admin' if r_r=="Quản lý" else 'staff', None, z_r, wp_in, p_r, None, "2000-01-01"))
                conn.commit(); st.success("Đăng ký thành công! Mời qua tab Đăng nhập.")
            except: st.error("Tên đăng nhập đã tồn tại.")

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
        if "session" in st.query_params:
            c.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],)); conn.commit()
            st.query_params.clear()
        del st.session_state.user; st.rerun()
    
    # Nút RESET KHẨN CẤP (Dành cho mọi user khi test)
    st.divider()
    if st.button("💣 XÓA DỮ LIỆU & LÀM LẠI TỪ ĐẦU", help="Bấm vào đây nếu muốn xóa sạch mọi thứ và đăng ký lại"):
        st.cache_resource.clear()
        try:
            c.close()
            conn.close()
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.success("Đã xóa sạch! Vui lòng F5 lại trang.")
        except Exception as e: st.error(f"Lỗi: {e}")

# --- SUPER ADMIN ---
if role == 'super_admin':
    st.header("🔑 SUPER ADMIN")
    k_t = st.selectbox("Loại Key", [30, 365]); 
    if st.button("Sinh Key"): 
        k = str(uuid.uuid4())[:8].upper(); c.execute("INSERT INTO license_keys VALUES (?,?,?)", (k, k_t, "active")); conn.commit(); st.success(f"Key: {k}")
    st.dataframe(pd.DataFrame(c.execute("SELECT * FROM license_keys").fetchall(), columns=["Key", "Days", "Status"]))
    st.stop()

# --- CHECK LICENSE ---
if role == 'admin':
    days = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if days < 0:
        st.error(f"🔒 Hết hạn!"); k_in = st.text_input("Nhập Key:")
        if st.button("Kích hoạt"):
            d = c.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (k_in,)).fetchone()
            if d:
                nex = (datetime.now()+timedelta(days=d[0])).strftime("%Y-%m-%d")
                c.execute("UPDATE users SET expiry_date=? WHERE username=?", (nex, user))
                c.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (k_in,)); conn.commit()
                st.session_state.expiry = nex; st.rerun()
            else: st.error("Lỗi Key!")
        st.stop()
    else: st.sidebar.success(f"✅ Bản quyền: {days} ngày")

# --- CHAT & WORK ---
tab_chat, tab_work = st.tabs(["💬 Chat", "📊 Công Việc"])

with tab_chat:
    active_room = wp_id
    if role == 'admin':
        rooms = [r[0] for r in c.execute("SELECT id FROM workplaces").fetchall()]
        if not rooms: st.warning("Tạo mã chi nhánh trước!"); 
        else: active_room = st.selectbox("Phòng:", rooms)
    
    if active_room:
        render_chat_box(active_room, zalo)
        c1, c2 = st.columns([5, 1])
        with c1:
            if p := st.chat_input("Nhập tin (@tag)..."):
                c.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", (active_room, zalo, p, datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.rerun()
        with c2:
            with st.popover("📎"):
                ec = st.columns(4)
                for i,e in enumerate(["👍","❤️","😂","OK"]): 
                    if ec[i].button(e): c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, e, datetime.now().strftime("%H:%M"), "emoji")); conn.commit(); st.rerun()
                img = st.file_uploader("Ảnh:", type=['png','jpg'])
                if img and st.button("Gửi"):
                    ext = img.name.split('.')[-1]; fname = f"{uuid.uuid4()}.{ext}"; fpath = os.path.join(IMG_FOLDER, fname)
                    with open(fpath, "wb") as f: f.write(img.getbuffer())
                    c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, fpath, datetime.now().strftime("%H:%M"), "image")); conn.commit(); st.rerun()

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
        st.metric("TỔNG NỢ", f"{total:,.0f} VNĐ")

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