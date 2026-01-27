import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
from datetime import datetime, timedelta

# --- CẤU HÌNH HỆ THỐNG ---
DB_FILE = "system_v20_full.db" # Database Full Tính Năng
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

# --- KHỞI TẠO BẢNG (ĐẦY ĐỦ CỘT) ---
def init_db():
    # 1. Users (9 cột)
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
                  qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT,
                  license_key TEXT, expiry_date TEXT)''')
    # 2. Workplaces
    c.execute('''CREATE TABLE IF NOT EXISTS workplaces
                 (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''')
    # 3. License Keys
    c.execute('''CREATE TABLE IF NOT EXISTS license_keys
                 (key_code TEXT PRIMARY KEY, duration_days INTEGER, status TEXT)''')
    # 4. Messages (6 cột - Có msg_type)
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, workplace_id TEXT, 
                  sender TEXT, content TEXT, timestamp TEXT, msg_type TEXT)''')
    # 5. Sessions
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (token TEXT PRIMARY KEY, username TEXT, expiry TEXT)''')
    conn.commit()

init_db()

# --- SUPER ADMIN ---
SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

st.set_page_config(page_title="Hệ Thống V20 Full", layout="wide", page_icon="💎")

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
    
    st.markdown("""
    <style>
        .tagged { background-color: #ffe6e6; border: 2px solid #ff4d4d; padding: 10px; border-radius: 10px; color: #b30000; font-weight: bold; margin-bottom: 5px;}
    </style>
    """, unsafe_allow_html=True)

    with st.container(height=450):
        if not msgs: st.info("👋 Chưa có tin nhắn nào.")
        for sender, content, ts, m_type in msgs:
            is_me = (sender == current_user_zalo)
            is_tagged = (m_type == 'text' and content and f"@{current_user_zalo}" in content)
            
            with st.chat_message("user" if is_me else "assistant", avatar="👤" if is_me else "🤖"):
                st.caption(f"{sender} • {ts}")
                if m_type == 'image':
                    if os.path.exists(content): st.image(content, width=250)
                elif m_type == 'emoji':
                    st.markdown(f"## {content}") 
                else:
                    if is_tagged:
                        st.markdown(f'<div class="tagged">🔔 @{current_user_zalo}, bạn được nhắc tên:<br>{content}</div>', unsafe_allow_html=True)
                    else:
                        st.write(content)

# ==========================================
# PHẦN ĐĂNG NHẬP / ĐĂNG KÝ
# ==========================================
if 'user' not in st.session_state:
    st.title("🔐 Hệ Thống V20 (Full Option)")
    t_log, t_reg, t_super = st.tabs(["Đăng nhập", "Đăng ký", "Super Admin"])
    
    with t_super:
        sa_u = st.text_input("User"); sa_p = st.text_input("Pass", type="password")
        if st.button("Login Super"):
            if sa_u == SUPER_ADMIN_USER and sa_p == SUPER_ADMIN_PASS:
                st.session_state.user = "SUPER_ADMIN"; st.session_state.role = "super_admin"
                st.rerun()

    with t_reg:
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
                conn.commit(); st.success("Đăng ký thành công! Mời đăng nhập.")
            except: st.error("Tên đăng nhập đã tồn tại.")

    with t_log:
        u_l = st.text_input("User ID", key="l_u"); p_l = st.text_input("Pass", type="password", key="l_p")
        if st.button("Đăng nhập"):
            c.execute('SELECT * FROM users WHERE username=? AND password=?', (u_l, p_l))
            ud = c.fetchone()
            if ud:
                st.session_state.user = ud[0]; st.session_state.role = ud[2]; st.session_state.zalo = ud[4]
                st.session_state.wp_id = ud[5]; st.session_state.expiry = ud[8]
                token = create_session(ud[0])
                st.query_params["session"] = token
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

# --- SUPER ADMIN PANEL ---
if role == 'super_admin':
    st.header("🔑 SUPER ADMIN")
    t1, t2 = st.tabs(["Tạo Key", "Reset Hệ Thống"])
    with t1:
        k_t = st.selectbox("Loại Key", [30, 365, 36500])
        if st.button("Sinh Key Mới"):
            key = str(uuid.uuid4())[:8].upper()
            c.execute("INSERT INTO license_keys VALUES (?,?,?)", (key, k_t, "active")); conn.commit()
            st.success(f"Key: {key}")
        st.write("Danh sách Key:"); c.execute("SELECT * FROM license_keys"); st.dataframe(pd.DataFrame(c.fetchall(), columns=["Key", "Days", "Status"]))
    with t2:
        if st.button("💣 XÓA TOÀN BỘ DỮ LIỆU"):
            c.execute("DROP TABLE users"); c.execute("DROP TABLE workplaces"); c.execute("DROP TABLE messages"); c.execute("DROP TABLE sessions"); c.execute("DROP TABLE license_keys"); conn.commit()
            init_db(); st.success("Đã Reset sạch sẽ!"); time.sleep(1); st.rerun()
    st.stop()

# --- CHECK LICENSE (ADMIN) ---
if role == 'admin':
    days = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if days < 0:
        st.error(f"🔒 TÀI KHOẢN HẾT HẠN! (Quá hạn {-days} ngày)"); 
        k_in = st.text_input("Nhập License Key:")
        if st.button("Kích hoạt"):
            c.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (k_in,))
            d = c.fetchone()
            if d:
                nex = (datetime.now()+timedelta(days=d[0])).strftime("%Y-%m-%d")
                c.execute("UPDATE users SET expiry_date=? WHERE username=?", (nex, user))
                c.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (k_in,)); conn.commit()
                st.session_state.expiry = nex; st.rerun()
            else: st.error("Key lỗi!")
        st.stop()
    else: st.sidebar.success(f"✅ Bản quyền: Còn {days} ngày")

# --- MAIN TABS ---
tab_chat, tab_work = st.tabs(["💬 Chat Đa Phương Tiện", "📊 Quản Lý Công Việc"])

# === TAB 1: CHAT PRO ===
with tab_chat:
    active_room = wp_id
    if role == 'admin':
        c.execute("SELECT id, name FROM workplaces")
        rooms = [r[0] for r in c.fetchall()]
        if not rooms: st.warning("Hãy tạo mã chi nhánh trước!"); 
        else: active_room = st.selectbox("Phòng chat:", rooms)
    
    if active_room:
        render_chat_box(active_room, zalo)

        col_input, col_media = st.columns([5, 1])
        with col_input:
            if prompt := st.chat_input("Nhập tin nhắn (Gõ @Tên để tag)..."):
                ts = datetime.now().strftime("%H:%M")
                c.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", 
                          (active_room, zalo, prompt, ts, "text"))
                conn.commit()
        
        with col_media:
            with st.popover("📎"):
                st.write("**Icon:**")
                ec1, ec2, ec3, ec4 = st.columns(4)
                if ec1.button("👍"): c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, "👍", datetime.now().strftime("%H:%M"), "emoji")); conn.commit()
                if ec2.button("❤️"): c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, "❤️", datetime.now().strftime("%H:%M"), "emoji")); conn.commit()
                if ec3.button("😂"): c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, "😂", datetime.now().strftime("%H:%M"), "emoji")); conn.commit()
                if ec4.button("OK"): c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, "OK", datetime.now().strftime("%H:%M"), "emoji")); conn.commit()
                
                st.divider()
                img = st.file_uploader("Ảnh:", type=['png','jpg'])
                if img and st.button("Gửi Ảnh"):
                    ext = img.name.split('.')[-1]; fname = f"{uuid.uuid4()}.{ext}"; fpath = os.path.join(IMG_FOLDER, fname)
                    with open(fpath, "wb") as f: f.write(img.getbuffer())
                    c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?, ?)", (active_room, zalo, fpath, datetime.now().strftime("%H:%M"), "image")); conn.commit()

# === TAB 2: QUẢN LÝ CÔNG VIỆC & LƯƠNG ===
with tab_work:
    if role == 'admin':
        # CẤU HÌNH CHI NHÁNH
        with st.expander("🏢 CẤU HÌNH CHI NHÁNH"):
            ni = st.text_input("Mã ID").upper(); nn = st.text_input("Tên")
            if st.button("Tạo Mã"): 
                try: c.execute("INSERT INTO workplaces VALUES (?,?,?)", (ni, nn, user)); conn.commit(); st.success(f"Xong: {ni}"); st.rerun()
                except: st.error("Trùng mã!")
            c.execute("SELECT id, name FROM workplaces"); st.dataframe(pd.DataFrame(c.fetchall(), columns=["ID", "Name"]))
        
        # LẤY DATA
        try: c.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'"); staffs = c.fetchall()
        except: staffs = []

        # CẢNH BÁO & TỔNG NỢ
        now = datetime.now(); alerts = []; total_sys_debt = 0
        for s in staffs:
            p = os.path.join(STORAGE, s[0], "salary.xlsx"); df_s = load_excel_safe(p)
            c_n = find_col(df_s, "ngày"); c_v = find_col(df_s, "vào"); c_tt = find_col(df_s, ["trạng thái", "nhận"]); c_tl = find_col(df_s, ["tổng", "lương"])
            
            if c_n and c_v:
                today_str = now.strftime("%Y-%m-%d")
                shifts = df_s[df_s[c_n].astype(str).str.contains(today_str, na=False)]
                for _, row in shifts.iterrows():
                    try:
                        h, m = map(int, str(row[c_v]).split(':')[:2]); shift_time = now.replace(hour=h, minute=m, second=0)
                        diff = (shift_time - now).total_seconds() / 60
                        if -15 < diff <= 60:
                            stt = "SẮP VÀO CA" if diff > 0 else "TRỄ"
                            alerts.append(f"⚠️ {stt} ({int(diff)}p): {s[1]} - SĐT: {s[3]}")
                    except: pass
            if c_tt and c_tl:
                total_sys_debt += pd.to_numeric(df_s[df_s[c_tt].astype(str).str.lower().str.contains('chưa', na=False)][c_tl], errors='coerce').sum()

        c_m1, c_m2 = st.columns(2)
        with c_m1: st.metric("TỔNG NỢ TOÀN HỆ THỐNG", f"{total_sys_debt:,.0f} VNĐ")
        with c_m2: 
            if alerts: st.error(f"Có {len(alerts)} cảnh báo!"); st.write(alerts)
            else: st.success("Không có cảnh báo.")

        st.divider()
        if staffs:
            all_wps = ["Tất cả"] + list(set([s[2] for s in staffs]))
            sel_wp = st.selectbox("Lọc Chi Nhánh", all_wps)
            filtered = [s for s in staffs if sel_wp == "Tất cả" or s[2] == sel_wp]
            s_map = {f"{s[1]} ({s[0]})": s[0] for s in filtered}
            sel_s = st.selectbox("Chọn Nhân Viên:", list(s_map.keys()))
            if sel_s:
                t_uid = s_map[sel_s]; p_path = os.path.join(STORAGE, t_uid, "salary.xlsx"); df_t = load_excel_safe(p_path)
                c_tt = find_col(df_t, ["trạng thái", "nhận"]); c_tl = find_col(df_t, ["tổng", "lương"])
                debt = 0
                if c_tt and c_tl: debt = pd.to_numeric(df_t[df_t[c_tt].astype(str).str.lower().str.contains('chưa', na=False)][c_tl], errors='coerce').sum()
                
                c_info, c_act = st.columns([2, 1])
                with c_info: st.metric(f"NỢ: {sel_s}", f"{debt:,.0f} VNĐ")
                with c_act:
                    if debt > 0 and st.button("💸 XÁC NHẬN THANH TOÁN"):
                        df_t.loc[df_t[c_tt].astype(str).str.lower().str.contains('chưa', na=False), c_tt] = "nhận"; df_t.to_excel(p_path, index=False)
                        msg = f"✅ Đã thanh toán {debt:,.0f} VNĐ cho @{sel_s}"; ts = datetime.now().strftime("%H:%M")
                        wp_send = [s[2] for s in staffs if s[0]==t_uid][0]
                        c.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", (wp_send, zalo, msg, ts, "text")); conn.commit()
                        st.success("Đã trả lương & báo tin!"); time.sleep(1); st.rerun()

                with st.expander("➕ Thêm Ca Làm"):
                    with st.form("add_shift"):
                        i_ng = st.date_input("Ngày", datetime.now()); i_vt = st.text_input("Vị trí")
                        c1, c2 = st.columns(2); 
                        with c1: i_v = st.time_input("Vào"); 
                        with c2: i_r = st.time_input("Ra")
                        i_l = st.number_input("Lương/h", value=20000)
                        if st.form_submit_button("Lưu"):
                            t_s = datetime.combine(i_ng, i_v); t_e = datetime.combine(i_ng, i_r)
                            if t_e < t_s: t_e += timedelta(days=1)
                            h = (t_e - t_s).total_seconds()/3600
                            new = {find_col(df_t,"ngày"):"%s"%i_ng, find_col(df_t,"vị trí"):i_vt, find_col(df_t,"tổng"):h*i_l, "Trạng thái":"chưa nhận", find_col(df_t,"vào"):"%s"%i_v, find_col(df_t,"ra"):"%s"%i_r, "Xác nhận đến":False}
                            pd.concat([df_t, pd.DataFrame([new])], ignore_index=True).to_excel(p_path, index=False); st.success("Đã thêm!"); st.rerun()
                st.dataframe(df_t)

    elif role == 'staff':
        st.subheader("💰 Ví & Công Việc")
        p = os.path.join(STORAGE, user); f = os.path.join(p, "salary.xlsx"); df = load_excel_safe(f)
        c_tt = find_col(df, ["trạng thái", "nhận"]); c_tl = find_col(df, ["tổng", "lương"])
        total_due = 0
        if c_tt and c_tl: total_due = pd.to_numeric(df[df[c_tt].astype(str).str.lower().str.contains('chưa', na=False)][c_tl], errors='coerce').sum()
        c_m1, c_m2 = st.columns([2, 1])
        with c_m1: st.metric("TIỀN QUÁN NỢ BẠN", f"{total_due:,.0f} VNĐ")
        with c_m2:
            if total_due > 0 and st.button("🔔 Đòi lương ngay"):
                 msg = f"📣 @Quản_lý ơi! Thanh toán lương cho em: {total_due:,.0f} VNĐ"; ts = datetime.now().strftime("%H:%M")
                 c.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", (wp_id, zalo, msg, ts, "text")); conn.commit(); st.toast("Đã gửi đòi nợ!", icon="💸")
        st.divider()
        with st.form("staff_add"):
            st.write("➕ Khai báo ca làm"); i_ng = st.date_input("Ngày", datetime.now()); i_vt = st.text_input("Vị trí", value=wp_id)
            c1, c2 = st.columns(2); 
            with c1: i_v = st.time_input("Vào"); 
            with c2: i_r = st.time_input("Ra")
            if st.form_submit_button("Lưu Ca"):
                t_s = datetime.combine(i_ng, i_v); t_e = datetime.combine(i_ng, i_r)
                if t_e < t_s: t_e += timedelta(days=1)
                h = (t_e - t_s).total_seconds()/3600
                new = {find_col(df,"ngày"):"%s"%i_ng, find_col(df,"vị trí"):i_vt, find_col(df,"tổng"):h*20000, "Trạng thái":"chưa nhận", find_col(df,"vào"):"%s"%i_v, find_col(df,"ra"):"%s"%i_r, "Xác nhận đến":False}
                pd.concat([df, pd.DataFrame([new])], ignore_index=True).to_excel(f, index=False); st.success("Lưu thành công!"); st.rerun()
        st.dataframe(df)