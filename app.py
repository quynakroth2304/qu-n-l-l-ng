import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
import shutil
from datetime import datetime, timedelta

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG V43 (ENTERPRISE STABILITY)
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống Quản Lý V43", 
    layout="wide", 
    page_icon="🛡️", 
    initial_sidebar_state="expanded"
)

# --- THIẾT LẬP DATABASE VÀ THƯ MỤC ---
DATABASE_FILE = "system_v43_stable.db"
STORAGE_DIRECTORY = "user_files"
UPLOAD_DIRECTORY = "chat_uploads"

# Tự động tạo thư mục nếu chưa tồn tại
if not os.path.exists(STORAGE_DIRECTORY):
    os.makedirs(STORAGE_DIRECTORY)
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

# --- CSS GIAO DIỆN CHUẨN (FIX LỖI HIỂN THỊ) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #f0f2f5;
    }

    /* Ẩn menu mặc định */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }

    /* THẺ THỐNG KÊ (METRIC CARD) */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        text-align: center;
        margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #0ea5e9;
        margin-bottom: 5px;
    }
    .metric-label {
        font-size: 13px;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
    }

    /* KHUNG CHAT (FIX HOÀN TOÀN LỖI VỠ KHUNG) */
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

    /* Tin nhắn bên Phải */
    .message-right {
        justify-content: flex-end;
    }
    .bubble-right {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        padding: 10px 16px;
        border-radius: 18px 18px 4px 18px;
        display: inline-block;
        max-width: 80%;
        min-width: 20px;
        text-align: left;
        word-wrap: break-word;
        white-space: pre-wrap;
        font-size: 15px;
        line-height: 1.5;
        box-shadow: 0 2px 5px rgba(37, 99, 235, 0.2);
    }

    /* Tin nhắn bên Trái */
    .message-left {
        justify-content: flex-start;
    }
    .bubble-left {
        background: #f1f5f9;
        color: #1e293b;
        padding: 10px 16px;
        border-radius: 18px 18px 18px 4px;
        display: inline-block;
        max-width: 80%;
        min-width: 20px;
        text-align: left;
        word-wrap: break-word;
        white-space: pre-wrap;
        font-size: 15px;
        line-height: 1.5;
        border: 1px solid #e2e8f0;
    }
    
    .chat-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        margin-right: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        object-fit: cover;
        flex-shrink: 0;
    }

    /* Nút bấm (Button) */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton > button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. XỬ LÝ DATABASE (KẾT NỐI AN TOÀN)
# ==============================================================================
@st.cache_resource
def get_database_connection():
    return sqlite3.connect(DATABASE_FILE, check_same_thread=False)

connection = get_database_connection()
cursor = connection.cursor()

def initialize_database_tables():
    # Bảng Người dùng
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            password TEXT, 
            role TEXT, 
            qr_path TEXT, 
            zalo_name TEXT, 
            workplace_id TEXT, 
            phone TEXT, 
            license_key TEXT, 
            expiry_date TEXT
        )
    ''')
    
    # Bảng Chi nhánh (Workplaces)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workplaces (
            id TEXT PRIMARY KEY, 
            name TEXT, 
            created_by TEXT
        )
    ''')
    
    # Bảng License Keys
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS license_keys (
            key_code TEXT PRIMARY KEY, 
            duration_days INTEGER, 
            status TEXT
        )
    ''')
    
    # Bảng Tin nhắn
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            workplace_id TEXT, 
            sender TEXT, 
            content TEXT, 
            timestamp TEXT, 
            msg_type TEXT
        )
    ''')
    
    # Bảng Phiên đăng nhập (Sessions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, 
            username TEXT, 
            expiry TEXT
        )
    ''')
    connection.commit()

# Khởi tạo bảng ngay khi chạy
initialize_database_tables()

# Tài khoản Quản trị viên Cấp cao (Cố định)
SUPER_ADMIN_USERNAME = "admin_vip"
SUPER_ADMIN_PASSWORD = "vip888"

# ==============================================================================
# 3. CÁC HÀM HỖ TRỢ (UTILITIES)
# ==============================================================================

def load_excel_safe(file_path):
    """Đọc file Excel an toàn, tránh lỗi thiếu cột."""
    required_columns = ["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]
    
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=required_columns)
    
    try:
        data_frame = pd.read_excel(file_path)
        # Bù các cột còn thiếu
        for column in required_columns:
            if column not in data_frame.columns:
                data_frame[column] = ""
        
        # Xử lý dữ liệu NaN (Rỗng) để tránh lỗi logic
        data_frame["Trạng thái"] = data_frame["Trạng thái"].fillna("chưa nhận").astype(str)
        data_frame["Xác nhận đến"] = data_frame["Xác nhận đến"].fillna(False)
        return data_frame
    except:
        return pd.DataFrame(columns=required_columns)

def save_excel_safe(data_frame, file_path):
    """Lưu file Excel an toàn, tự tạo thư mục cha."""
    directory_path = os.path.dirname(file_path)
    if directory_path and not os.path.exists(directory_path):
        os.makedirs(directory_path)
    data_frame.to_excel(file_path, index=False)

def get_avatar_url(name):
    """Tạo Avatar dựa trên tên."""
    return f"https://ui-avatars.com/api/?name={name}&background=0ea5e9&color=fff&size=128&bold=true"

# --- Quản lý Phiên đăng nhập ---
def create_login_session(username):
    token = str(uuid.uuid4())
    expiry_time = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, expiry_time))
    connection.commit()
    return token

def verify_session_token(token):
    try:
        cursor.execute("SELECT username, expiry FROM sessions WHERE token=?", (token,))
        row = cursor.fetchone()
        if row:
            expiry_string = row[1]
            if datetime.strptime(expiry_string, "%Y-%m-%d %H:%M:%S") > datetime.now():
                return row[0] # Trả về username
    except:
        pass
    return None

# --- Khởi tạo Session State An Toàn (VÁ LỖI ATTRIBUTE ERROR) ---
def initialize_session_state():
    """Hàm này đảm bảo các biến session luôn tồn tại."""
    if 'user' not in st.session_state:
        # Kiểm tra token trong URL để tự động đăng nhập
        if "session" in st.query_params:
            token = st.query_params["session"]
            auto_username = verify_session_token(token)
            
            if auto_username:
                # Lấy thông tin user từ DB
                cursor.execute('SELECT * FROM users WHERE username=?', (auto_username,))
                user_data = cursor.fetchone()
                if user_data:
                    st.session_state.user = user_data[0]
                    st.session_state.role = user_data[2]
                    st.session_state.zalo = user_data[4]
                    st.session_state.wp_id = user_data[5]
                    st.session_state.expiry = user_data[8]
                    return # Đã khởi tạo xong

        # Nếu không có token hoặc token lỗi -> Set về None
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.zalo = None
        st.session_state.wp_id = None
        st.session_state.expiry = None

# Gọi hàm khởi tạo ngay đầu chương trình
initialize_session_state()

# ==============================================================================
# 4. CÁC THÀNH PHẦN GIAO DIỆN (UI FRAGMENTS)
# ==============================================================================

@st.fragment(run_every=2)
def render_chat_window(room_id, current_user_name, chat_mode="group"):
    try:
        cursor.execute("SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,))
        messages = cursor.fetchall()[::-1] # Đảo ngược để tin mới nhất ở dưới
    except:
        return

    chat_icon = "🏢" if chat_mode == "group" else "💬"
    display_name = room_id if chat_mode == "group" else "Tin nhắn riêng"
    
    st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:12px; margin-bottom:15px;'>{chat_icon} <b>{display_name}</b></div>", unsafe_allow_html=True)

    html_content = '<div class="chat-container">'
    last_sender = None
    
    for sender, content, timestamp, msg_type in messages:
        is_me = (sender == current_user_name)
        
        if is_me:
            html_content += '<div class="message-row message-right">'
        else:
            html_content += '<div class="message-row message-left">'
            # Chỉ hiện avatar nếu người gửi khác người trước
            if sender != last_sender:
                avatar_url = get_avatar_url(sender)
                html_content += f'<img src="{avatar_url}" class="chat-avatar" title="{sender}">'
            else:
                html_content += '<div style="width:46px;"></div>' # Khoảng trống thay cho avatar

        message_body = ""
        
        if msg_type == 'image':
            import base64
            if os.path.exists(content):
                with open(content, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode()
                message_body = f'<img src="data:image/png;base64,{image_base64}" style="max-width:250px; border-radius:12px;">'
            else:
                message_body = "<i>⚠️ Hình ảnh đã bị xóa</i>"
        
        elif msg_type == 'emoji':
            message_body = f'<div style="font-size:40px; line-height:1;">{content}</div>'
            
        elif msg_type == 'call':
            link_parts = content.split('|')
            link = link_parts[-1]
            icon = "📹" if "video" in content else "📞"
            message_body = f'''
            <div style="background:#e0f2fe; padding:10px; border-radius:10px; border:1px solid #bae6fd;">
                <div style="font-size:18px; margin-bottom:5px;">{icon} <b>{sender}</b> đang gọi...</div>
                <a href="{link}" target="_blank" style="background:#0284c7; color:white; padding:5px 15px; border-radius:20px; text-decoration:none; font-weight:bold; font-size:12px;">Tham gia ngay</a>
            </div>
            '''
        
        else: # Tin nhắn văn bản
            # Highlight tag tên
            if f"@{current_user_name}" in content:
                content = f"<span style='background-color:#fef08a; padding:2px 5px; border-radius:4px; font-weight:bold;'>{content}</span>"
            message_body = content

        # Render bong bóng chat
        if msg_type in ['emoji', 'call']:
            html_content += f'<div>{message_body}</div>'
        else:
            bubble_class = "bubble-right" if is_me else "bubble-left"
            name_tag = ""
            if chat_mode == "group" and not is_me and sender != last_sender:
                name_tag = f"<div style='font-size:11px; color:#64748b; margin-bottom:2px; margin-left:5px;'>{sender}</div>"
            
            html_content += f'<div>{name_tag}<div class="{bubble_class}" title="{timestamp}">{message_body}</div></div>'

        html_content += '</div>' # Đóng thẻ hàng
        last_sender = sender

    html_content += '</div>' # Đóng container
    st.markdown(html_content, unsafe_allow_html=True)
    
    # Javascript tự cuộn xuống cuối
    st.markdown("""
        <script>
            var chatDiv = window.parent.document.querySelector('.chat-container');
            if (chatDiv) { chatDiv.scrollTop = chatDiv.scrollHeight; }
        </script>
    """, unsafe_allow_html=True)

@st.fragment
def render_dashboard(staff_list):
    if not staff_list:
        st.warning("Chưa có dữ liệu nhân viên.")
        return

    total_debt = 0
    staff_count = len(staff_list)
    pending_approval_count = 0
    
    for staff in staff_list:
        staff_username = staff[0]
        file_path = os.path.join(STORAGE_DIRECTORY, staff_username, "salary.xlsx")
        data_frame = load_excel_safe(file_path)
        
        # Tính nợ: Lấy tất cả trạng thái KHÔNG PHẢI "đã nhận"
        if "Trạng thái" in data_frame.columns and "Tổng lương" in data_frame.columns:
            unpaid_rows = data_frame[~data_frame["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)]
            total_debt += pd.to_numeric(unpaid_rows["Tổng lương"], errors='coerce').sum()
            
        if "Xác nhận đến" in data_frame.columns:
            # Đếm số ca chưa được xác nhận (False)
            pending_shifts = data_frame[data_frame["Xác nhận đến"].astype(str).str.lower() == "false"]
            pending_approval_count += len(pending_shifts)

    column1, column2, column3 = st.columns(3)
    with column1:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{staff_count}</div><div class="metric-label">Nhân sự</div></div>""", unsafe_allow_html=True)
    with column2:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{total_debt:,.0f}</div><div class="metric-label">Tổng Quỹ Lương</div></div>""", unsafe_allow_html=True)
    with column3:
        status_color = "#ef4444" if pending_approval_count > 0 else "#22c55e"
        st.markdown(f"""<div class="metric-card"><div class="metric-value" style="color:{status_color}">{pending_approval_count}</div><div class="metric-label">Ca chưa xác nhận</div></div>""", unsafe_allow_html=True)
    st.write("")

# ==============================================================================
# 5. MÀN HÌNH ĐĂNG NHẬP & ĐĂNG KÝ
# ==============================================================================
if st.session_state.user is None:
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        st.markdown("<h1 style='text-align: center; color: #0ea5e9;'>🛡️ HỆ THỐNG V43 ENTERPRISE</h1>", unsafe_allow_html=True)
        
        tab_login, tab_register, tab_super = st.tabs(["Đăng Nhập", "Đăng Ký Mới", "Super Admin"])
        
        # --- TAB LOGIN ---
        with tab_login:
            login_username = st.text_input("Tên đăng nhập")
            login_password = st.text_input("Mật khẩu", type="password")
            
            if st.button("Đăng nhập", type="primary", use_container_width=True):
                cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (login_username, login_password))
                user_data = cursor.fetchone()
                
                if user_data:
                    # Gán session state
                    st.session_state.user = user_data[0]
                    st.session_state.role = user_data[2]
                    st.session_state.zalo = user_data[4]
                    st.session_state.wp_id = user_data[5]
                    st.session_state.expiry = user_data[8]
                    
                    token = create_login_session(user_data[0])
                    st.query_params["session"] = token
                    st.rerun()
                else:
                    st.error("Tên đăng nhập hoặc mật khẩu không đúng.")

        # --- TAB REGISTER ---
        with tab_register:
            reg_col1, reg_col2 = st.columns(2)
            with reg_col1:
                reg_username = st.text_input("User ID (Viết liền)", key="reg_u")
                reg_name = st.text_input("Tên hiển thị (Zalo)", key="reg_n")
                reg_phone = st.text_input("Số điện thoại", key="reg_p")
            with reg_col2:
                reg_password = st.text_input("Mật khẩu", type="password", key="reg_pass")
                reg_role = st.radio("Đăng ký vai trò:", ["Nhân viên", "Quản lý"], horizontal=True)
                
                reg_workplace = "ADMIN"
                manager_activation_key = ""
                
                if reg_role == "Nhân viên":
                    reg_workplace = st.text_input("Mã Chi Nhánh")
                elif reg_role == "Quản lý":
                    manager_activation_key = st.text_input("🔑 Nhập Key Kích Hoạt (Từ Admin)", type="password")
            
            if st.button("Tạo Tài Khoản", use_container_width=True):
                if not reg_username or not reg_password or not reg_name:
                    st.warning("Vui lòng điền đầy đủ thông tin.")
                else:
                    try:
                        # Kiểm tra logic nghiệp vụ
                        if reg_role == "Nhân viên":
                            cursor.execute("SELECT id FROM workplaces WHERE id=?", (reg_workplace,))
                            if not cursor.fetchone():
                                st.error("Mã Chi Nhánh không tồn tại!")
                                st.stop()
                        
                        if reg_role == "Quản lý":
                            cursor.execute("SELECT key_code FROM license_keys WHERE key_code=? AND status='active'", (manager_activation_key,))
                            valid_key = cursor.fetchone()
                            if not valid_key:
                                st.error("Key kích hoạt sai hoặc đã hết hạn!")
                                st.stop()
                            else:
                                cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (manager_activation_key,))
                        
                        # Xóa dữ liệu cũ nếu trùng ID (Tránh hiện ca cũ)
                        old_user_path = os.path.join(STORAGE_DIRECTORY, reg_username)
                        if os.path.exists(old_user_path):
                            shutil.rmtree(old_user_path)
                        
                        cursor.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', 
                                       (reg_username, reg_password, 'admin' if reg_role=="Quản lý" else 'staff', 
                                        None, reg_name, reg_workplace, reg_phone, None, "2099-01-01"))
                        connection.commit()
                        st.success("✅ Đăng ký thành công! Vui lòng đăng nhập.")
                        
                    except sqlite3.IntegrityError:
                        st.error("Tên đăng nhập này đã được sử dụng.")

        # --- TAB SUPER ADMIN (FIX ATTRIBUTE ERROR) ---
        with tab_super:
            super_user = st.text_input("Super User")
            super_pass = st.text_input("Super Password", type="password")
            
            if st.button("Truy Cập Hệ Thống Gốc", use_container_width=True):
                if super_user == SUPER_ADMIN_USERNAME and super_pass == SUPER_ADMIN_PASSWORD:
                    # Gán giá trị đặc biệt cho Super Admin để tránh lỗi AttributeError
                    st.session_state.user = "SUPER_ADMIN"
                    st.session_state.role = "super_admin"
                    st.session_state.zalo = "Super Admin" # QUAN TRỌNG: Phải có giá trị này
                    st.session_state.wp_id = "MASTER"     # QUAN TRỌNG: Phải có giá trị này
                    st.rerun()
                else:
                    st.error("Thông tin đăng nhập không chính xác.")
    
    st.stop() # Dừng chương trình nếu chưa đăng nhập

# ==============================================================================
# 6. MÀN HÌNH CHÍNH (LOGGED IN)
# ==============================================================================
# Lấy thông tin session hiện tại (Đã an toàn nhờ hàm khởi tạo)
current_user = st.session_state.user
current_role = st.session_state.role
current_zalo = st.session_state.zalo
current_workplace = st.session_state.wp_id

# --- SIDEBAR ---
with st.sidebar:
    st.image(get_avatar_url(current_zalo), width=100)
    st.title(current_zalo)
    st.caption(f"ID: {current_user}")
    st.caption(f"Chức vụ: {current_role}")
    
    if current_workplace and current_workplace != "ADMIN" and current_workplace != "MASTER":
        st.caption(f"Chi nhánh: {current_workplace}")
    
    st.divider()
    
    if st.button("🚪 Đăng xuất", use_container_width=True):
        if "session" in st.query_params:
            cursor.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],))
            connection.commit()
            st.query_params.clear()
        
        # Xóa session state an toàn
        st.session_state.user = None
        st.rerun()

# --- SUPER ADMIN PANEL ---
if current_role == 'super_admin':
    st.header("🔧 SUPER ADMIN CONSOLE")
    tab_keys, tab_reset = st.tabs(["Quản Lý Key", "Dữ Liệu Hệ Thống"])
    
    with tab_keys:
        st.subheader("Tạo Key Kích Hoạt Mới")
        key_type = st.selectbox("Loại Key", ["30 Ngày", "365 Ngày", "Vĩnh viễn"])
        if st.button("Sinh Key Mới"):
            new_key = str(uuid.uuid4())[:8].upper()
            duration = 36500 if key_type == "Vĩnh viễn" else (365 if key_type == "365 Ngày" else 30)
            cursor.execute("INSERT INTO license_keys VALUES (?,?,?)", (new_key, duration, "active"))
            connection.commit()
            st.success(f"Key vừa tạo: {new_key}")
        
        st.dataframe(pd.read_sql_query("SELECT * FROM license_keys", connection))

    with tab_reset:
        st.error("⚠️ VÙNG NGUY HIỂM: Hành động không thể hoàn tác")
        if st.button("💣 XÓA SẠCH TOÀN BỘ DỮ LIỆU (HARD RESET)"):
            st.cache_resource.clear()
            cursor.close()
            connection.close()
            
            if os.path.exists(DATABASE_FILE):
                os.remove(DATABASE_FILE)
            
            if os.path.exists(STORAGE_DIRECTORY):
                shutil.rmtree(STORAGE_DIRECTORY)
                os.makedirs(STORAGE_DIRECTORY)
                
            if os.path.exists(UPLOAD_DIRECTORY):
                shutil.rmtree(UPLOAD_DIRECTORY)
                os.makedirs(UPLOAD_DIRECTORY)
                
            st.success("Đã Reset toàn bộ hệ thống! Vui lòng nhấn F5.")
            st.stop()
    st.stop() # Super Admin chỉ thấy panel này

# --- CHECK LICENSE (ADMIN) ---
if current_role == 'admin':
    days_left = (datetime.strptime(st.session_state.expiry or "2000-01-01", "%Y-%m-%d") - datetime.now()).days
    if days_left < 0:
        st.error(f"🔒 Tài khoản hết hạn! (Quá hạn {-days_left} ngày)")
        renewal_key = st.text_input("Nhập Key gia hạn:")
        if st.button("Kích hoạt ngay"):
            key_data = cursor.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (renewal_key,)).fetchone()
            if key_data:
                new_expiry_date = (datetime.now() + timedelta(days=key_data[0])).strftime("%Y-%m-%d")
                cursor.execute("UPDATE users SET expiry_date=? WHERE username=?", (new_expiry_date, current_user))
                cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (renewal_key,))
                connection.commit()
                st.session_state.expiry = new_expiry_date
                st.success("Gia hạn thành công!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Key không hợp lệ hoặc đã sử dụng.")
        st.stop()

# --- TABS ỨNG DỤNG CHÍNH ---
tab_communication, tab_tasks = st.tabs(["💬 Trung Tâm Liên Lạc", "📊 Quản Lý & Công Việc"])

# === TAB 1: CHAT ===
with tab_communication:
    chat_mode_selection = st.radio("", ["🏢 Nhóm Chung", "👤 Nhắn Riêng"], horizontal=True, label_visibility="collapsed")
    active_room_id = None
    
    if chat_mode_selection == "🏢 Nhóm Chung":
        if current_role == 'admin':
            # Admin thấy tất cả chi nhánh
            rooms_data = cursor.execute("SELECT id FROM workplaces").fetchall()
            rooms_list = [r[0] for r in rooms_data]
            active_room_id = st.selectbox("Chọn Chi nhánh:", rooms_list) if rooms_list else None
        else:
            # Nhân viên chỉ thấy chi nhánh của mình
            active_room_id = current_workplace
    else:
        # Nhắn tin riêng
        users_data = cursor.execute("SELECT zalo_name FROM users WHERE username != ?", (current_user,)).fetchall()
        users_list = [u[0] for u in users_data]
        if users_list:
            target_user = st.selectbox("Chọn người nhắn:", users_list)
            # Tạo Room ID duy nhất
            user_pair = sorted([current_zalo, target_user])
            active_room_id = f"DM_{user_pair[0]}_{user_pair[1]}"

    if active_room_id:
        render_chat_window(active_room_id, current_zalo, "group" if chat_mode_selection == "🏢 Nhóm Chung" else "private")
        
        column_input, column_tools = st.columns([6, 1])
        with column_input:
            message_input = st.chat_input("Nhập tin nhắn...")
            if message_input:
                cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", 
                               (active_room_id, current_zalo, message_input, datetime.now().strftime("%H:%M"), "text"))
                connection.commit()
        
        with column_tools:
            with st.popover("➕", use_container_width=True):
                if st.button("📹 Call Video", use_container_width=True):
                    call_link = f"https://meet.jit.si/call_{uuid.uuid4()}"
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                   (active_room_id, current_zalo, f"video|{call_link}", datetime.now().strftime("%H:%M"), "call"))
                    connection.commit()
                    st.rerun()
                
                uploaded_image = st.file_uploader("", type=['png','jpg'], label_visibility="collapsed")
                if uploaded_image and st.button("Gửi Ảnh", use_container_width=True):
                    file_extension = uploaded_image.name.split('.')[-1]
                    file_name = f"{uuid.uuid4()}.{file_extension}"
                    file_path = os.path.join(UPLOAD_DIRECTORY, file_name)
                    
                    with open(file_path, "wb") as f:
                        f.write(uploaded_image.getbuffer())
                    
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                   (active_room_id, current_zalo, file_path, datetime.now().strftime("%H:%M"), "image"))
                    connection.commit()
                    st.rerun()

# === TAB 2: CÔNG VIỆC ===
with tab_tasks:
    # --- GIAO DIỆN QUẢN LÝ ---
    if current_role == 'admin':
        # 1. Quản lý Chi nhánh
        with st.expander("🏢 QUẢN LÝ CHI NHÁNH"):
            create_tab, list_tab = st.tabs(["Tạo Mới", "Danh Sách"])
            with create_tab:
                c1, c2 = st.columns(2)
                with c1: new_id = st.text_input("Mã Chi Nhánh (VD: Q1)").upper()
                with c2: new_name = st.text_input("Tên Hiển Thị (VD: Cafe Quận 1)")
                if st.button("Tạo Chi Nhánh Mới"):
                    try:
                        cursor.execute("INSERT INTO workplaces VALUES (?,?,?)", (new_id, new_name, current_user))
                        connection.commit()
                        st.success("Thành công!")
                        st.rerun()
                    except:
                        st.error("Mã này đã tồn tại.")
            with list_tab:
                my_branches = pd.read_sql_query(f"SELECT * FROM workplaces WHERE created_by='{current_user}'", connection)
                st.dataframe(my_branches)

        # 2. Dashboard tổng quan
        staff_list = cursor.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        render_dashboard(staff_list)
        
        # 3. Quản lý chi tiết nhân viên
        if staff_list:
            st.divider()
            selected_staff_label = st.selectbox("📝 Chọn nhân viên:", [f"{s[1]} ({s[0]})" for s in staff_list])
            target_id = selected_staff_label.split('(')[1].replace(')', '')
            target_file_path = os.path.join(STORAGE_DIRECTORY, target_id, "salary.xlsx")
            df_salary = load_excel_safe(target_file_path)
            
            # Logic tính toán
            pending_shifts_count = len(df_salary[df_salary["Xác nhận đến"].astype(str).str.lower() == "false"])
            current_debt = pd.to_numeric(df_salary[~df_salary["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)]["Tổng lương"], errors='coerce').sum()
            
            st.info(f"Thông tin liên hệ: {staff_list[[s[0] for s in staff_list].index(target_id)][3]}")
            
            col_action1, col_action2, col_action3 = st.columns(3)
            with col_action1: st.metric("Nợ lương:", f"{current_debt:,.0f} VNĐ")
            with col_action2: st.metric("Ca chưa duyệt:", f"{pending_shifts_count}")
            
            with col_action3:
                # Nút Duyệt chấm công
                if pending_shifts_count > 0:
                    if st.button("✅ DUYỆT CHẤM CÔNG (Xác nhận đến)", use_container_width=True):
                        df_salary.loc[df_salary["Xác nhận đến"].astype(str).str.lower() == "false", "Xác nhận đến"] = True
                        save_excel_safe(df_salary, target_file_path)
                        st.success("Đã duyệt thành công!")
                        time.sleep(1)
                        st.rerun()
                
                # Nút Báo chuyển khoản
                if current_debt > 0:
                    if st.button("💸 BÁO ĐÃ CHUYỂN KHOẢN", use_container_width=True):
                        mask = ~df_salary["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)
                        df_salary.loc[mask, "Trạng thái"] = "chờ xác nhận"
                        save_excel_safe(df_salary, target_file_path)
                        
                        # Gửi tin nhắn thông báo
                        target_wp = [s[2] for s in staff_list if s[0] == target_id][0]
                        cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                       (target_wp, current_zalo, f"🔔 Đã chuyển khoản lương: {current_debt:,.0f}. Vui lòng xác nhận!", datetime.now().strftime("%H:%M"), "text"))
                        connection.commit()
                        st.success("Đã gửi thông báo cho nhân viên!")
                        st.rerun()
            
            with st.expander("➕ Thêm Ca Làm Việc (Admin)"):
                with st.form("admin_add_shift"):
                    d = st.date_input("Ngày"); v = st.text_input("Vị trí", "Tại quán")
                    t1 = st.time_input("Vào"); t2 = st.time_input("Ra")
                    r = st.number_input("Lương/h (VNĐ)", value=20000, step=1000)
                    
                    if st.form_submit_button("Lưu Ca", use_container_width=True):
                        dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                        if dt2 < dt1: dt2 += timedelta(days=1)
                        h = (dt2 - dt1).total_seconds() / 3600
                        new_row = pd.DataFrame([{
                            "Ngày": d.strftime("%Y-%m-%d"), 
                            "Vị trí": v, 
                            "Giờ vào": t1.strftime("%H:%M"), 
                            "Giờ ra": t2.strftime("%H:%M"), 
                            "Tổng lương": h * r, 
                            "Trạng thái": "chưa nhận", 
                            "Xác nhận đến": True # Admin tạo thì auto duyệt
                        }])
                        df_salary = pd.concat([df_salary, new_row], ignore_index=True)
                        save_excel_safe(df_salary, target_file_path)
                        st.success("Đã thêm ca thành công!")
                        st.rerun()
            
            st.dataframe(df_salary, use_container_width=True)

    # --- GIAO DIỆN NHÂN VIÊN ---
    elif current_role == 'staff':
        my_file_path = os.path.join(STORAGE_DIRECTORY, current_user, "salary.xlsx")
        df_my_salary = load_excel_safe(my_file_path)
        
        # Tính nợ: Các dòng chưa "đã nhận"
        mask_unpaid = ~df_my_salary["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)
        my_debt = pd.to_numeric(df_my_salary[mask_unpaid]["Tổng lương"], errors='coerce').sum()
        
        # Check chờ xác nhận
        waiting_confirmation = len(df_my_salary[df_my_salary["Trạng thái"].astype(str).str.lower() == "chờ xác nhận"]) > 0
        
        col_s1, col_s2 = st.columns(2)
        with col_s1: st.metric("💰 Quán nợ bạn:", f"{my_debt:,.0f} VNĐ")
        with col_s2: 
            if waiting_confirmation:
                st.warning("Quản lý đã báo chuyển tiền!")
                if st.button("✅ XÁC NHẬN ĐÃ NHẬN TIỀN", use_container_width=True):
                    df_my_salary.loc[df_my_salary["Trạng thái"].astype(str).str.lower() == "chờ xác nhận", "Trạng thái"] = "đã nhận"
                    save_excel_safe(df_my_salary, my_file_path)
                    
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                   (current_workplace, current_zalo, "✅ Em đã nhận được tiền lương rồi ạ!", datetime.now().strftime("%H:%M"), "text"))
                    connection.commit()
                    st.success("Đã xác nhận thành công!")
                    st.rerun()
            elif my_debt > 0:
                if st.button("🔔 Nhắc Quản lý", use_container_width=True):
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                   (current_workplace, current_zalo, f"📣 Anh/Chị ơi check lương giúp em: {my_debt:,.0f} VNĐ", datetime.now().strftime("%H:%M"), "text"))
                    connection.commit()
                    st.toast("Đã gửi tin nhắn nhắc nhở!")
        
        with st.expander("➕ Báo cáo ca làm việc", expanded=True):
            with st.form("staff_add_shift"):
                d = st.date_input("Ngày"); v = st.text_input("Vị trí", current_workplace)
                t1 = st.time_input("Vào"); t2 = st.time_input("Ra")
                sr = st.number_input("Mức lương/giờ (VNĐ)", value=20000, step=1000)
                
                if st.form_submit_button("Gửi báo cáo", use_container_width=True):
                    dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                    if dt2 < dt1: dt2 += timedelta(days=1)
                    h = (dt2 - dt1).total_seconds() / 3600
                    new_row = pd.DataFrame([{
                        "Ngày": d.strftime("%Y-%m-%d"), 
                        "Vị trí": v, 
                        "Giờ vào": t1.strftime("%H:%M"), 
                        "Giờ ra": t2.strftime("%H:%M"), 
                        "Tổng lương": h * sr, 
                        "Trạng thái": "chưa nhận", 
                        "Xác nhận đến": False # Chờ duyệt
                    }])
                    df_my_salary = pd.concat([df_my_salary, new_row], ignore_index=True)
                    save_excel_safe(df_my_salary, my_file_path)
                    st.success("Đã lưu báo cáo! Vui lòng chờ quản lý duyệt.")
                    st.rerun()
        
        st.dataframe(df_my_salary, use_container_width=True)