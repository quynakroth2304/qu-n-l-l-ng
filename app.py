import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import hashlib
from datetime import datetime, timedelta

# --- CẤU HÌNH ---
DB_FILE = "system_v19_fixed.db" 
STORAGE = "user_files"
IMG_FOLDER = "chat_uploads"

if not os.path.exists(STORAGE): os.makedirs(STORAGE)
if not os.path.exists(IMG_FOLDER): os.makedirs(IMG_FOLDER)

# --- 1. KẾT NỐI DATABASE AN TOÀN ---
@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")  # Tăng hiệu năng
    return conn

def execute_db(query, params=(), fetch=False, fetch_one=False):
    """Hàm thực thi database an toàn - FIX lỗi cursor toàn cục"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if fetch_one:
            result = cursor.fetchone()
            return result
        elif fetch:
            result = cursor.fetchall()
            return result
        else:
            conn.commit()
            return None
    except Exception as e:
        conn.rollback()
        st.error(f"Database error: {str(e)}")
        return None if fetch or fetch_one else False
    finally:
        cursor.close()

# --- KHỞI TẠO BẢNG ---
def init_database():
    queries = [
        '''CREATE TABLE IF NOT EXISTS users
           (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
            qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT,
            license_key TEXT, expiry_date TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS workplaces
           (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS license_keys
           (key_code TEXT PRIMARY KEY, duration_days INTEGER, status TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS messages
           (id INTEGER PRIMARY KEY AUTOINCREMENT, workplace_id TEXT, 
            sender TEXT, content TEXT, timestamp TEXT, msg_type TEXT)''',
        
        '''CREATE TABLE IF NOT EXISTS sessions
           (token TEXT PRIMARY KEY, username TEXT, expiry TEXT)'''
    ]
    
    for query in queries:
        execute_db(query)

init_database()

# --- BẢO MẬT: HASH PASSWORD ---
def hash_password(password):
    """FIX: Mã hóa mật khẩu thay vì lưu plain text"""
    return hashlib.sha256(password.encode()).hexdigest()

# --- SUPER ADMIN ---
SUPER_ADMIN_USER = "admin"
SUPER_ADMIN_PASS = hash_password("123")

st.set_page_config(page_title="Hệ Thống V19 (Fixed)", layout="wide", page_icon="✅")

# --- 2. HÀM HỖ TRỢ ---
def find_col(df, keywords):
    if isinstance(keywords, str): keywords = [keywords]
    for col in df.columns:
        for key in keywords:
            if key.lower() in str(col).lower(): return col
    return None

def load_excel_safe(path):
    """FIX: Xử lý exception cụ thể và báo lỗi rõ ràng"""
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", 
                                      "Tổng lương", "Trạng thái", "Xác nhận đến"])
    try:
        return pd.read_excel(path, engine='openpyxl')
    except ImportError:
        st.error("⚠️ Cài đặt: pip install openpyxl")
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"⚠️ Lỗi đọc file {os.path.basename(path)}: {str(e)}")
        return pd.DataFrame()

def ensure_user_folder(uid):
    """FIX: Tạo thư mục và file Excel nếu chưa có"""
    user_path = os.path.join(STORAGE, uid)
    if not os.path.exists(user_path):
        os.makedirs(user_path)
    
    salary_file = os.path.join(user_path, "salary.xlsx")
    if not os.path.exists(salary_file):
        df_init = pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", 
                                         "Tổng lương", "Trạng thái", "Xác nhận đến"])
        df_init.to_excel(salary_file, index=False)
    
    return salary_file

# --- 3. SESSION & AUTO LOGIN ---
def create_session(username):
    token = str(uuid.uuid4())
    exp = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    execute_db("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, exp))
    return token

def get_user_from_session(token):
    row = execute_db("SELECT username, expiry FROM sessions WHERE token=?", (token,), fetch_one=True)
    if row:
        expiry = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
        if expiry > datetime.now():
            return row[0]
        else:
            execute_db("DELETE FROM sessions WHERE token=?", (token,))
    return None

# AUTO LOGIN
if "session" in st.query_params:
    auto_user = get_user_from_session(st.query_params["session"])
    if auto_user and 'user' not in st.session_state:
        ud = execute_db('SELECT * FROM users WHERE username=?', (auto_user,), fetch_one=True)
        if ud:
            st.session_state.user = ud[0]
            st.session_state.role = ud[2]
            st.session_state.zalo = ud[4]
            st.session_state.wp_id = ud[5]
            st.session_state.expiry = ud[8]

# ==========================================
# PHẦN 4: GIAO DIỆN CHAT (REAL-TIME - ĐÃ FIX)
# ==========================================
@st.fragment(run_every=2)  # FIX: Tăng từ 1s lên 2s để giảm tải
def render_chat_box(room_id, current_user_zalo):
    """FIX: Cache messages và chỉ load khi có thay đổi"""
    
    # Kiểm tra số lượng tin nhắn
    count = execute_db("SELECT COUNT(*) FROM messages WHERE workplace_id=?", 
                       (room_id,), fetch_one=True)
    msg_count = count[0] if count else 0
    
    # Chỉ load lại khi có tin nhắn mới HOẶC đổi phòng
    cache_key = f"chat_{room_id}"
    if (cache_key not in st.session_state or 
        st.session_state.get(f"{cache_key}_count", 0) != msg_count):
        
        msgs = execute_db(
            "SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50",
            (room_id,), fetch=True
        )
        st.session_state[cache_key] = msgs[::-1] if msgs else []
        st.session_state[f"{cache_key}_count"] = msg_count
    
    msgs = st.session_state.get(cache_key, [])
    
    st.caption(f"⚡ Chat Room: **{room_id}** ({msg_count} tin)")
    
    st.markdown("""
    <style>
        .tagged { 
            background-color: #fff2cc; 
            border: 1px solid #ffc107; 
            padding: 5px; 
            border-radius: 5px; 
            font-weight: bold; 
            color: #333; 
        }
    </style>
    """, unsafe_allow_html=True)

    with st.container(height=450):
        if not msgs:
            st.write("*(Chưa có tin nhắn)*")
        else:
            for sender, content, ts, m_type in msgs:
                is_me = (sender == current_user_zalo)
                is_tagged = (m_type == 'text' and content and f"@{current_user_zalo}" in content)
                
                with st.chat_message("user" if is_me else "assistant", avatar="👤" if is_me else "🤖"):
                    st.write(f"**{sender}** _({ts})_")
                    
                    if m_type == 'image':
                        if os.path.exists(content): 
                            st.image(content, width=200)
                    elif m_type == 'emoji':
                        st.markdown(f"### {content}") 
                    else:
                        if is_tagged:
                            st.markdown(f'<div class="tagged">🔔 {content}</div>', unsafe_allow_html=True)
                        else:
                            st.write(content)

# ==========================================
# PHẦN 5: GIAO DIỆN ĐĂNG NHẬP/ĐĂNG KÝ
# ==========================================
if 'user' not in st.session_state:
    st.title("🚀 Hệ Thống V19 (Fixed Version)")
    t_log, t_reg, t_super = st.tabs(["Đăng nhập", "Đăng ký", "Super Admin"])
    
    with t_super:
        sa_u = st.text_input("User", key="su")
        sa_p = st.text_input("Pass", type="password", key="sp")
        if st.button("Login Super", key="sl"):
            if sa_u == SUPER_ADMIN_USER and hash_password(sa_p) == SUPER_ADMIN_PASS:
                st.session_state.user = "SUPER_ADMIN"
                st.session_state.role = "super_admin"
                st.rerun()
            else:
                st.error("❌ Sai thông tin Super Admin!")

    with t_reg:
        st.subheader("📝 Đăng ký tài khoản")
        c1, c2 = st.columns(2)
        with c1:
            u_r = st.text_input("User ID (3-20 ký tự)", key="r_u")
            z_r = st.text_input("Zalo Name", key="r_z")
            p_r = st.text_input("Số điện thoại", key="r_p")
        with c2:
            pass_r = st.text_input("Mật khẩu (tối thiểu 4 ký tự)", type="password", key="r_pa")
            r_r = st.radio("Vai trò", ["Nhân viên", "Quản lý"], horizontal=True)
        
        wp_in = st.text_input("Mã Chi Nhánh (Nhân viên phải nhập)", key="r_w") if r_r == "Nhân viên" else "ADMIN"
        
        if st.button("✅ Đăng ký ngay", key="rb"):
            # FIX: Validation đầu vào
            if len(u_r) < 3 or len(u_r) > 20:
                st.error("❌ User ID phải từ 3-20 ký tự!")
                st.stop()
            
            if len(pass_r) < 4:
                st.error("❌ Mật khẩu phải ít nhất 4 ký tự!")
                st.stop()
            
            if not z_r.strip():
                st.error("❌ Vui lòng nhập Zalo Name!")
                st.stop()
            
            # Kiểm tra chi nhánh (nếu là nhân viên)
            if r_r == "Nhân viên":
                if not wp_in.strip():
                    st.error("❌ Nhân viên phải nhập mã chi nhánh!")
                    st.stop()
                
                wp_exists = execute_db("SELECT id FROM workplaces WHERE id=?", (wp_in,), fetch_one=True)
                if not wp_exists:
                    st.error(f"❌ Mã chi nhánh '{wp_in}' không tồn tại! Liên hệ quản lý.")
                    st.stop()
            
            # FIX: Hash password trước khi lưu
            result = execute_db(
                'INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)',
                (u_r, hash_password(pass_r), 'admin' if r_r=="Quản lý" else 'staff', 
                 None, z_r, wp_in, p_r, None, "2099-01-01")
            )
            
            if result is not False:
                # FIX: Tạo thư mục user ngay sau khi đăng ký
                ensure_user_folder(u_r)
                st.success(f"✅ Đăng ký thành công! Hãy đăng nhập với User: {u_r}")
            else:
                st.error("❌ User ID đã tồn tại hoặc lỗi hệ thống!")

    with t_log:
        st.subheader("🔐 Đăng nhập")
        u_l = st.text_input("User ID", key="l_u")
        p_l = st.text_input("Mật khẩu", type="password", key="l_p")
        
        if st.button("🚀 Đăng nhập", key="lb"):
            # FIX: So sánh password đã hash
            ud = execute_db(
                'SELECT * FROM users WHERE username=? AND password=?',
                (u_l, hash_password(p_l)), fetch_one=True
            )
            
            if ud:
                st.session_state.user = ud[0]
                st.session_state.role = ud[2]
                st.session_state.zalo = ud[4]
                st.session_state.wp_id = ud[5]
                st.session_state.expiry = ud[8]
                
                # Tạo session token
                token = create_session(ud[0])
                st.query_params["session"] = token
                
                st.success(f"✅ Chào mừng {ud[4]}!")
                st.rerun()
            else:
                st.error("❌ Sai User ID hoặc mật khẩu!")
    
    st.stop()

# --- SAU KHI LOGIN ---
user = st.session_state.user
role = st.session_state.role
zalo = st.session_state.get('zalo', user)
wp_id = st.session_state.get('wp_id', "")

with st.sidebar:
    st.title(f"👋 {zalo}")
    st.caption(f"🎭 Vai trò: **{role}**")
    st.caption(f"🏢 Chi nhánh: **{wp_id}**")
    
    if st.button("🚪 Đăng xuất"):
        if "session" in st.query_params:
            execute_db("DELETE FROM sessions WHERE token=?", (st.query_params["session"],))
            st.query_params.clear()
        
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        st.rerun()

# --- SUPER ADMIN ---
if role == 'super_admin':
    st.header("🔑 SUPER ADMIN PANEL")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ XÓA TOÀN BỘ DATABASE", type="primary"):
            try:
                tables = ['users', 'workplaces', 'messages', 'sessions', 'license_keys']
                for table in tables:
                    execute_db(f"DROP TABLE IF EXISTS {table}")
                st.success("✅ Đã xóa sạch! F5 để khởi tạo lại.")
            except Exception as e:
                st.error(f"Lỗi: {e}")
    
    with col2:
        if st.button("📊 Xem thống kê"):
            users_count = execute_db("SELECT COUNT(*) FROM users", fetch_one=True)
            msgs_count = execute_db("SELECT COUNT(*) FROM messages", fetch_one=True)
            wp_count = execute_db("SELECT COUNT(*) FROM workplaces", fetch_one=True)
            
            st.metric("Tổng Users", users_count[0] if users_count else 0)
            st.metric("Tổng Tin nhắn", msgs_count[0] if msgs_count else 0)
            st.metric("Tổng Chi nhánh", wp_count[0] if wp_count else 0)
    
    st.stop()

# --- MAIN TABS ---
tab_chat, tab_work = st.tabs(["💬 Chat", "📊 Công Việc"])

# === TAB 1: CHAT ===
with tab_chat:
    active_room = wp_id
    
    if role == 'admin':
        rooms_data = execute_db("SELECT id, name FROM workplaces", fetch=True)
        rooms = [r[0] for r in rooms_data] if rooms_data else []
        
        if not rooms:
            st.warning("⚠️ Chưa có chi nhánh! Tạo ở tab 'Công Việc'")
        else:
            active_room = st.selectbox("🏢 Chọn phòng chat:", rooms, key="room_select")
    
    if active_room:
        # Render Chat Box
        render_chat_box(active_room, zalo)

        # Input Area
        c1, c2 = st.columns([5, 1])
        
        with c1:
            if prompt := st.chat_input("💬 Nhập tin nhắn..."):
                ts = datetime.now().strftime("%H:%M")
                execute_db(
                    "INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)",
                    (active_room, zalo, prompt, ts, "text")
                )
                # Clear cache để force reload
                cache_key = f"chat_{active_room}"
                if cache_key in st.session_state:
                    del st.session_state[cache_key]
                st.rerun()
        
        with c2:
            with st.popover("📷"):
                if st.button("👍", key="like_btn"): 
                    execute_db(
                        "INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)",
                        (active_room, zalo, "👍", datetime.now().strftime("%H:%M"), "emoji")
                    )
                    st.rerun()
                
                img = st.file_uploader("📤 Gửi ảnh", type=['png','jpg','jpeg'], key="img_up")
                if img and st.button("✅ Gửi ảnh"):
                    ext = img.name.split('.')[-1]
                    fname = f"{uuid.uuid4()}.{ext}"
                    fpath = os.path.join(IMG_FOLDER, fname)
                    
                    with open(fpath, "wb") as f:
                        f.write(img.getbuffer())
                    
                    execute_db(
                        "INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)",
                        (active_room, zalo, fpath, datetime.now().strftime("%H:%M"), "image")
                    )
                    st.rerun()

# === TAB 2: CÔNG VIỆC ===
with tab_work:
    if role == 'admin':
        # === QUẢN LÝ CHI NHÁNH ===
        with st.expander("🏢 QUẢN LÝ CHI NHÁNH"):
            col1, col2 = st.columns(2)
            with col1:
                new_id = st.text_input("Mã ID chi nhánh", key="wp_id").upper().strip()
                new_name = st.text_input("Tên chi nhánh", key="wp_name").strip()
            
            with col2:
                st.write("")
                st.write("")
                if st.button("➕ Tạo chi nhánh", type="primary"):
                    if not new_id or not new_name:
                        st.error("❌ Vui lòng điền đầy đủ thông tin!")
                    else:
                        result = execute_db(
                            "INSERT INTO workplaces VALUES (?,?,?)",
                            (new_id, new_name, user)
                        )
                        if result is not False:
                            st.success(f"✅ Đã tạo chi nhánh: {new_id} - {new_name}")
                            st.rerun()
                        else:
                            st.error("❌ Mã ID đã tồn tại!")
        
        st.divider()
        
        # === QUẢN LÝ NHÂN VIÊN ===
        st.subheader("👥 QUẢN LÝ NHÂN VIÊN")
        
        staffs = execute_db(
            "SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'",
            fetch=True
        )
        
        if not staffs:
            st.info("📭 Chưa có nhân viên nào")
        else:
            # Tính tổng nợ
            total_debt = 0
            for s in staffs:
                p_path = ensure_user_folder(s[0])  # FIX: Đảm bảo file tồn tại
                df = load_excel_safe(p_path)
                
                c_tt = find_col(df, ["trạng thái", "nhận"])
                c_tl = find_col(df, ["tổng", "lương"])
                
                if c_tt and c_tl and not df.empty:
                    debt_rows = df[df[c_tt].astype(str).str.lower().str.contains('chưa', na=False)]
                    total_debt += pd.to_numeric(debt_rows[c_tl], errors='coerce').sum()
            
            st.metric("💰 TỔNG NỢ LƯƠNG", f"{total_debt:,.0f} VNĐ")
            
            # Chọn nhân viên
            s_sel = st.selectbox(
                "Chọn nhân viên",
                [f"{s[1]} ({s[0]}) - {s[2]}" for s in staffs],
                key="staff_sel"
            )
            uid = s_sel.split("(")[1].split(")")[0]
            
            # Load dữ liệu nhân viên
            p_path = ensure_user_folder(uid)  # FIX: Đảm bảo thư mục tồn tại
            df_t = load_excel_safe(p_path)
            
            # Tính nợ cá nhân
            c_tt = find_col(df_t, ["trạng thái", "nhận"])
            c_tl = find_col(df_t, ["tổng", "lương"])
            debt = 0
            
            if c_tt and c_tl and not df_t.empty:
                debt_rows = df_t[df_t[c_tt].astype(str).str.lower().str.contains('chưa', na=False)]
                debt = pd.to_numeric(debt_rows[c_tl], errors='coerce').sum()
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.metric(f"Nợ {s_sel.split('(')[0].strip()}", f"{debt:,.0f} VNĐ")
            
            with col2:
                if debt > 0 and st.button("💵 Thanh toán", type="primary"):
                    # Đánh dấu đã trả
                    df_t.loc[df_t[c_tt].astype(str).str.lower().str.contains('chưa', na=False), c_tt] = "Đã nhận"
                    df_t.to_excel(p_path, index=False)
                    
                    # Gửi thông báo
                    staff_wp = [s[2] for s in staffs if s[0] == uid][0]
                    execute_db(
                        "INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)",
                        (staff_wp, zalo, f"✅ Đã trả lương: {debt:,.0f} VNĐ", 
                         datetime.now().strftime("%H:%M"), "text")
                    )
                    
                    st.success(f"✅ Đã thanh toán {debt:,.0f} VNĐ!")
                    st.rerun()
            
            # Thêm ca làm việc
            with st.expander("➕ Thêm ca làm việc"):
                with st.form("add_shift"):
                    c1, c2 = st.columns(2)
                    with c1:
                        d = st.date_input("📅 Ngày làm")
                        v = st.text_input("📍 Vị trí", value=[s[2] for s in staffs if s[0] == uid][0])
                    
                    with c2:
                        t1 = st.time_input("🕐 Giờ vào")
                        t2 = st.time_input("🕐 Giờ ra")
                    
                    luong_gio = st.number_input("💵 Lương/giờ (VNĐ)", value=20000, step=5000)
                    
                    # FIX: Hiển thị preview tính lương
                    start = datetime.combine(d, t1)
                    end = datetime.combine(d, t2)
                    if end < start:
                        end += timedelta(days=1)
                    
                    hours = (end - start).total_seconds() / 3600
                    total_salary = hours * luong_gio
                    
                    st.info(f"⏱️ Tổng giờ: **{hours:.2f}h** → Lương: **{total_salary:,.0f} VNĐ**")
                    
                    if st.form_submit_button("✅ Lưu ca", type="primary"):
                        new_row = {
                            find_col(df_t, "ngày"): str(d),
                            find_col(df_t, "vị trí"): v,
                            find_col(df_t, "vào"): str(t1),
                            find_col(df_t, "ra"): str(t2),
                            find_col(df_t, "tổng"): total_salary,
                            "Trạng thái": "Chưa nhận",
                            "Xác nhận đến": False
                        }
                        
                        df_t = pd.concat([df_t, pd.DataFrame([new_row])], ignore_index=True)
                        df_t.to_excel(p_path, index=False)
                        
                        st.success(f"✅ Đã thêm ca: {d} - {hours:.2f}h - {total_salary:,.0f} VNĐ")
                        st.rerun()
            
            # Hiển thị bảng lương
            st.dataframe(df_t, use_container_width=True)
    
    elif role == 'staff':
        st.subheader("💼 VÍ CỦA TÔI")
        
        # FIX: Đảm bảo file tồn tại
        p_path = ensure_user_folder(user)
        df = load_excel_safe(p_path)
        
        # Tính tổng nợ
        c_tt = find_col(df, ["trạng thái", "nhận"])
        c_tl = find_col(df, ["tổng", "lương"])
        total_due = 0
        
        if c_tt and c_tl and not df.empty:
            debt_rows = df[df[c_tt].astype(str).str.lower().str.contains('chưa', na=False)]
            total_due = pd.to_numeric(debt_rows[c_tl], errors='coerce').sum()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.metric("💰 Đang nợ bạn", f"{total_due:,.0f} VNĐ")
        
        with col2:
            if total_due > 0 and st.button("📣 Đòi tiền", type="primary"):
                execute_db(
                    "INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)",
                    (wp_id, zalo, f"📣 Trả lương em đi: {total_due:,.0f} VNĐ", 
                     datetime.now().strftime("%H:%M"), "text")
                )
                st.toast("✅ Đã gửi yêu cầu đến quản lý!")
        
        # Thêm ca làm việc
        with st.expander("➕ Thêm ca làm việc"):
            with st.form("staff_add"):
                c1, c2 = st.columns(2)
                with c1:
                    d = st.date_input("📅 Ngày làm")
                    v = st.text_input("📍 Vị trí", value=wp_id)
                
                with c2:
                    t1 = st.time_input("🕐 Giờ vào")
                    t2 = st.time_input("🕐 Giờ ra")
                
                luong_gio = st.number_input("💵 Lương/giờ (VNĐ)", value=20000, step=5000)
                
                # Preview
                start = datetime.combine(d, t1)
                end = datetime.combine(d, t2)
                if end < start:
                    end += timedelta(days=1)
                
                hours = (end - start).total_seconds() / 3600
                total_salary = hours * luong_gio
                
                st.info(f"⏱️ Tổng giờ: **{hours:.2f}h** → Lương: **{total_salary:,.0f} VNĐ**")
                
                if st.form_submit_button("✅ Lưu Ca", type="primary"):
                    new_row = {
                        find_col(df, "ngày"): str(d),
                        find_col(df, "vị trí"): v,
                        find_col(df, "vào"): str(t1),
                        find_col(df, "ra"): str(t2),
                        find_col(df, "tổng"): total_salary,
                        "Trạng thái": "Chưa nhận",
                        "Xác nhận đến": False
                    }
                    
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_excel(p_path, index=False)
                    
                    st.success(f"✅ Đã thêm ca: {d} - {hours:.2f}h - {total_salary:,.0f} VNĐ")
                    st.rerun()
        
        # Hiển thị bảng lương
        st.dataframe(df, use_container_width=True)
