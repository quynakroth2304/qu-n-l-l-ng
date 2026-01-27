import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- CẤU HÌNH ---
DB_FILE = "system_v10.db"
STORAGE = "user_files"
if not os.path.exists(STORAGE): os.makedirs(STORAGE)

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# 1. Bảng users (Thêm cột license_key, expiry_date cho Admin)
c.execute('''CREATE TABLE IF NOT EXISTS users
             (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
              qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT,
              license_key TEXT, expiry_date TEXT)''')

# 2. Bảng workplaces
c.execute('''CREATE TABLE IF NOT EXISTS workplaces
             (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''')

# 3. Bảng keys (Kho key do Super Admin tạo)
c.execute('''CREATE TABLE IF NOT EXISTS license_keys
             (key_code TEXT PRIMARY KEY, duration_days INTEGER, status TEXT)''')

# 4. Bảng tin nhắn (Chat)
c.execute('''CREATE TABLE IF NOT EXISTS messages
             (id INTEGER PRIMARY KEY AUTOINCREMENT, workplace_id TEXT, 
              sender TEXT, content TEXT, timestamp TEXT)''')
conn.commit()

# --- SUPER ADMIN CONFIG (Tài khoản trùm mặc định) ---
SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

# --- HÀM HỖ TRỢ ---
def find_col(df, keywords):
    if isinstance(keywords, str): keywords = [keywords]
    for col in df.columns:
        for key in keywords:
            if key.lower() in str(col).lower(): return col
    return None

def highlight_hours(val):
    try:
        hours = float(val)
        if hours >= 8: return 'background-color: #d4edda; color: green' 
        elif hours < 4 and hours > 0: return 'background-color: #f8d7da; color: red'
    except: pass
    return ''

# Hàm xin quyền thông báo trình duyệt
def request_notification_permission():
    js = """
    <script>
    if (!("Notification" in window)) {
        alert("Trình duyệt này không hỗ trợ thông báo.");
    } else {
        Notification.requestPermission().then(function (permission) {
            if (permission === "granted") {
                console.log("Đã cấp quyền thông báo!");
            }
        });
    }
    </script>
    """
    components.html(js, height=0)

st.set_page_config(page_title="Hệ Thống V10 Pro", layout="wide")

# ==========================================
# PHẦN 1: MÀN HÌNH ĐĂNG NHẬP
# ==========================================
if 'user' not in st.session_state:
    st.title("🔐 Hệ Thống Quản Lý & Chat Nhóm (V10)")
    
    t_log, t_reg, t_super = st.tabs(["Đăng nhập", "Đăng ký Thành viên", "🔑 Super Admin (Tạo Key)"])
    
    # --- TAB SUPER ADMIN ---
    with t_super:
        st.caption("Khu vực dành cho chủ sở hữu phần mềm")
        sa_user = st.text_input("Super User")
        sa_pass = st.text_input("Super Password", type="password")
        if st.button("Truy cập kho Key"):
            if sa_user == SUPER_ADMIN_USER and sa_pass == SUPER_ADMIN_PASS:
                st.session_state.user = "SUPER_ADMIN"
                st.session_state.role = "super_admin"
                st.rerun()
            else: st.error("Sai tài khoản trùm!")

    # --- TAB ĐĂNG KÝ (Logic cũ) ---
    with t_reg:
        c1, c2 = st.columns(2)
        with c1: 
            u_r = st.text_input("Tên đăng nhập", key="r_u")
            z_r = st.text_input("Tên Zalo", key="r_z")
            phone_r = st.text_input("SĐT", key="r_p")
        with c2: 
            p_r = st.text_input("Mật khẩu", type='password', key="r_pass")
        
        r_r = st.radio("Vai trò:", ["Nhân viên", "Quản lý"], horizontal=True, key="r_r")
        
        wp_id_input = ""
        if r_r == "Nhân viên":
            wp_id_input = st.text_input("Nhập Mã Chi Nhánh (Do quản lý cấp)", key="r_wp").strip()
        else:
            st.info("Quản lý sẽ được dùng thử hoặc cần nhập Key để kích hoạt.")

        if st.button("Đăng ký", key="btn_reg"):
            if u_r and p_r and z_r and phone_r:
                try:
                    role_code = 'admin' if r_r == "Quản lý" else 'staff'
                    final_wp = "ADMIN"
                    if role_code == 'staff':
                        c.execute("SELECT id FROM workplaces WHERE id=?", (wp_id_input,))
                        if not c.fetchone():
                            st.error("Mã chi nhánh không đúng!"); st.stop()
                        final_wp = wp_id_input
                    
                    # Admin mới tạo chưa có key, expiry là ngày quá khứ
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', 
                              (u_r, p_r, role_code, None, z_r, final_wp, phone_r, None, "2000-01-01"))
                    conn.commit()
                    st.success("Đăng ký thành công!"); 
                except: st.error("Tên đăng nhập đã tồn tại.")

    # --- TAB ĐĂNG NHẬP ---
    with t_log:
        u_l = st.text_input("Tên đăng nhập", key="l_u")
        p_l = st.text_input("Mật khẩu", type='password', key="l_p")
        if st.button("Vào hệ thống", key="btn_log"):
            c.execute('SELECT * FROM users WHERE username=? AND password=?', (u_l, p_l))
            ud = c.fetchone()
            if ud:
                st.session_state.user = ud[0]
                st.session_state.role = ud[2]
                st.session_state.zalo = ud[4]
                st.session_state.wp_id = ud[5]
                st.session_state.expiry = ud[8] # Ngày hết hạn
                st.rerun()
            else: st.error("Sai thông tin!")
    st.stop()

# ==========================================
# PHẦN 2: LOGIC SAU KHI ĐĂNG NHẬP
# ==========================================
user = st.session_state.user
role = st.session_state.role

# --- GIAO DIỆN SUPER ADMIN (TẠO KEY) ---
if role == 'super_admin':
    st.title("🔑 KHO KEY (SUPER ADMIN)")
    if st.button("Đăng xuất"): 
        del st.session_state.user; st.rerun()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Tạo Key Mới")
        k_type = st.selectbox("Loại Key", ["30 Ngày", "1 Năm", "Vĩnh viễn"])
        if st.button("Sinh Key"):
            days = 30 if k_type == "30 Ngày" else 365 if k_type == "1 Năm" else 36500
            new_key = str(uuid.uuid4())[:8].upper() # Key ngắn gọn 8 ký tự
            c.execute("INSERT INTO license_keys VALUES (?,?,?)", (new_key, days, "active"))
            conn.commit()
            st.success(f"Key mới: {new_key} ({days} ngày)")
            
    with c2:
        st.subheader("Danh sách Key")
        c.execute("SELECT * FROM license_keys")
        st.dataframe(pd.DataFrame(c.fetchall(), columns=["Mã Key", "Số ngày", "Trạng thái"]))
    st.stop() # Dừng, không hiện phần dưới

# --- KIỂM TRA BẢN QUYỀN (CHO ADMIN) ---
if role == 'admin':
    expiry_str = st.session_state.expiry
    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d") if expiry_str else datetime(2000,1,1)
    days_left = (expiry_date - datetime.now()).days

    if days_left < 0:
        st.error("🔒 TÀI KHOẢN HẾT HẠN HOẶC CHƯA KÍCH HOẠT!")
        st.info("Vui lòng liên hệ nhà cung cấp để mua Key mới.")
        
        key_input = st.text_input("Nhập License Key để kích hoạt:")
        if st.button("Kích hoạt ngay"):
            c.execute("SELECT duration_days, status FROM license_keys WHERE key_code=? AND status='active'", (key_input,))
            key_data = c.fetchone()
            if key_data:
                # Tính ngày hết hạn mới
                new_expiry = (datetime.now() + timedelta(days=key_data[0])).strftime("%Y-%m-%d")
                # Cập nhật user
                c.execute("UPDATE users SET license_key=?, expiry_date=? WHERE username=?", (key_input, new_expiry, user))
                # Hủy key đã dùng
                c.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (key_input,))
                conn.commit()
                st.session_state.expiry = new_expiry
                st.success("✅ Kích hoạt thành công! Vui lòng tải lại trang.")
                time.sleep(2)
                st.rerun()
            else:
                st.error("Key không tồn tại hoặc đã được sử dụng!")
        st.stop() # Chặn không cho dùng tiếp
    else:
        st.sidebar.success(f"✅ Bản quyền: Còn {days_left} ngày")

# ==========================================
# PHẦN 3: GIAO DIỆN CHÍNH (ADMIN & STAFF)
# ==========================================
zalo = st.session_state.zalo
wp_id = st.session_state.wp_id

# Xin quyền thông báo (Chạy 1 lần)
request_notification_permission()

with st.sidebar:
    st.title(f"👋 {zalo}")
    st.caption(f"Role: {role} | Work: {wp_id}")
    if st.button("Đăng xuất"):
        del st.session_state.user; st.rerun()

# --- CHAT NHÓM (DÙNG CHUNG) ---
# Xác định Room Chat (Admin thấy hết hoặc chọn, Staff chỉ thấy của mình)
chat_room = wp_id
if role == 'admin':
    # Admin quản lý Mã chi nhánh
    with st.expander("🏢 QUẢN LÝ MÃ CHI NHÁNH"):
        c1, c2 = st.columns([1,2])
        with c1:
            n_code = st.text_input("Mã Mới").upper()
            n_name = st.text_input("Tên Chi Nhánh")
            if st.button("Tạo Mã"):
                try: 
                    c.execute("INSERT INTO workplaces VALUES (?,?,?)", (n_code, n_name, user)); conn.commit(); st.rerun()
                except: st.error("Mã tồn tại!")
        with c2:
            c.execute("SELECT id, name FROM workplaces")
            wps = [row[0] for row in c.fetchall()]
            st.dataframe(pd.DataFrame(wps, columns=["Mã ID"]))
    
    # Admin chọn phòng chat
    chat_room = st.selectbox("💬 Chọn nhóm Chat:", wps if wps else ["Chưa có nhóm"])

# Giao diện Chat
with st.expander(f"💬 TRÒ CHUYỆN NHÓM: {chat_room}", expanded=False):
    # Load tin nhắn
    c.execute("SELECT sender, content, timestamp FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (chat_room,))
    msgs = c.fetchall()[::-1] # Đảo ngược để tin mới nhất ở dưới
    
    chat_container = st.container(height=300)
    for sender, content, ts in msgs:
        with chat_container.chat_message("user" if sender == zalo else "assistant"):
            st.write(f"**{sender}**: {content}")
            st.caption(ts)

    # Gửi tin nhắn
    if prompt := st.chat_input("Nhập tin nhắn (@ten để tag)..."):
        ts_now = datetime.now().strftime("%H:%M %d/%m")
        c.execute("INSERT INTO messages (workplace_id, sender, content, timestamp) VALUES (?,?,?,?)", 
                  (chat_room, zalo, prompt, ts_now))
        conn.commit()
        st.rerun()

# --- GIAO DIỆN NHÂN VIÊN (ĐÒI NỢ) ---
if role == 'staff':
    st.header("💰 Ví Của Tôi")
    
    # Tạo/Đọc file lương
    p_me = os.path.join(STORAGE, user)
    if not os.path.exists(p_me): os.makedirs(p_me)
    f_me = os.path.join(p_me, "salary.xlsx")
    
    if not os.path.exists(f_me):
        pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]).to_excel(f_me, index=False)
    
    df = pd.read_excel(f_me)
    c_tt = find_col(df, ["trạng thái", "nhận"])
    c_tl = find_col(df, ["tổng", "lương"])
    
    # Tính tổng tiền quán nợ
    total_due = 0
    if c_tt and c_tl:
        due_df = df[df[c_tt].astype(str).str.lower().str.contains('chưa', na=False)]
        total_due = pd.to_numeric(due_df[c_tl], errors='coerce').sum()
    
    # HIỂN THỊ TIỀN & NÚT ĐÒI
    c_m1, c_m2 = st.columns([2, 1])
    with c_m1:
        st.metric("TỔNG TIỀN QUÁN ĐANG NỢ BẠN", f"{total_due:,.0f} VNĐ", delta="Chưa thanh toán")
    with c_m2:
        if total_due > 0:
            st.warning("⚠️ Bạn có lương chưa nhận!")
            if st.button("🔔 Gửi Yêu Cầu Thanh Toán"):
                # Gửi 1 tin nhắn vào nhóm chat để đòi tiền
                msg = f"📣 @Quản_lý ơi! Thanh toán lương cho em: {total_due:,.0f} VNĐ nhé!"
                ts = datetime.now().strftime("%H:%M %d/%m")
                c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?)", (wp_id, zalo, msg, ts))
                conn.commit()
                st.success("Đã gửi yêu cầu vào nhóm Chat!")
                time.sleep(1)
                st.rerun()
        else:
            st.success("✅ Đã nhận đủ lương.")

    # Bảng chi tiết & Thêm ca
    st.divider()
    t1, t2 = st.tabs(["➕ Khai báo ca làm", "📋 Lịch sử làm việc"])
    
    with t1:
        with st.form("staff_add"):
            i_ng = st.date_input("Ngày", datetime.now())
            i_vt = st.text_input("Vị trí", value=wp_id)
            c1, c2 = st.columns(2)
            with c1: i_v = st.time_input("Vào")
            with c2: i_r = st.time_input("Ra")
            if st.form_submit_button("Lưu Ca"):
                t_s = datetime.combine(i_ng, i_v); t_e = datetime.combine(i_ng, i_r)
                if t_e < t_s: t_e += timedelta(days=1)
                h = (t_e - t_s).total_seconds()/3600
                new = {find_col(df, "ngày"):"%s"%i_ng, find_col(df, "vị trí"):i_vt, c_tl:h*20000, c_tt:"chưa nhận", find_col(df,"vào"):"%s"%i_v, find_col(df,"ra"):"%s"%i_r, "Xác nhận đến":False}
                pd.concat([df, pd.DataFrame([new])], ignore_index=True).to_excel(f_me, index=False)
                st.success("Lưu thành công!"); st.rerun()
                
    with t2:
        st.dataframe(df)

# --- GIAO DIỆN QUẢN LÝ (XEM NỢ & THANH TOÁN) ---
if role == 'admin':
    st.header("📊 Quản Lý Tài Chính & Nhân Sự")
    
    # Lấy danh sách nhân viên
    try: c.execute("SELECT username, zalo_name, workplace_id FROM users WHERE role='staff'"); staffs = c.fetchall()
    except: staffs = []
    
    if not staffs: st.info("Chưa có nhân viên."); st.stop()
    
    # Bộ lọc
    wps = ["Tất cả"] + list(set([s[2] for s in staffs]))
    sel_wp = st.selectbox("Lọc Chi Nhánh", wps)
    filtered_staffs = [s for s in staffs if sel_wp == "Tất cả" or s[2] == sel_wp]
    
    # Chọn nhân viên
    s_map = {f"{s[1]} ({s[0]})": s[0] for s in filtered_staffs}
    sel_staff = st.selectbox("Chọn Nhân Viên:", list(s_map.keys()))
    
    if sel_staff:
        t_uid = s_map[sel_staff]
        p_path = os.path.join(STORAGE, t_uid, "salary.xlsx")
        
        if os.path.exists(p_path):
            df_t = pd.read_excel(p_path)
            c_tt = find_col(df_t, ["trạng thái", "nhận"])
            c_tl = find_col(df_t, ["tổng", "lương"])
            
            # Tính nợ
            debt_rows = df_t[df_t[c_tt].astype(str).str.lower().str.contains('chưa', na=False)]
            debt = pd.to_numeric(debt_rows[c_tl], errors='coerce').sum()
            
            st.divider()
            c_info, c_act = st.columns([2, 1])
            with c_info:
                st.metric(f"NỢ LƯƠNG: {sel_staff}", f"{debt:,.0f} VNĐ", delta_color="inverse")
            with c_act:
                if debt > 0:
                    if st.button("💸 XÁC NHẬN ĐÃ THANH TOÁN"):
                        df_t.loc[debt_rows.index, c_tt] = "nhận"
                        df_t.to_excel(p_path, index=False)
                        
                        # Gửi thông báo vào nhóm chat
                        msg = f"✅ Đã thanh toán {debt:,.0f} VNĐ cho @{sel_staff.split('(')[0].strip()}"
                        ts = datetime.now().strftime("%H:%M %d/%m")
                        # Lấy wp_id của nhân viên để gửi đúng nhóm
                        staff_wp = [s[2] for s in staffs if s[0] == t_uid][0]
                        c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?)", (staff_wp, zalo, msg, ts))
                        conn.commit()
                        
                        st.success("Đã cập nhật trạng thái & báo tin!"); time.sleep(1); st.rerun()
                else: st.success("Nhân viên này đã nhận đủ lương.")
            
            st.dataframe(df_t)