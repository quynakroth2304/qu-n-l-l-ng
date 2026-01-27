import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
from datetime import datetime, timedelta

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG & CSS GIAO DIỆN (BEAUTY UI)
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống V31 Ultimate",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="expanded"
)

# Tên Database và Thư mục lưu trữ
DB_FILE = "system_v31_ultimate.db"
STORAGE_DIR = "user_files"
UPLOAD_DIR = "chat_uploads"

# Tự động tạo các thư mục hệ thống ngay khi khởi động
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- CSS TÙY CHỈNH (Làm đẹp giao diện) ---
st.markdown("""
<style>
    /* Import Font chữ hiện đại */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
        background-color: #f0f2f5; /* Màu nền Facebook nhạt */
    }

    /* Ẩn Menu mặc định của Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Tùy chỉnh Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #ddd;
    }

    /* Card Thống kê (Dashboard) */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        text-align: center;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #1877f2; /* Xanh Facebook */
        margin-bottom: 5px;
    }
    .metric-label {
        font-size: 14px;
        color: #65676b;
        text-transform: uppercase;
        font-weight: 500;
    }

    /* Giao diện Chat (Messenger Style) */
    .chat-container {
        padding: 20px;
        background: white;
        border-radius: 15px;
        height: 65vh;
        overflow-y: auto;
        border: 1px solid #ddd;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.02);
    }
    
    /* Tin nhắn của Tôi (Bên phải) */
    .msg-right {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 8px;
        align-items: flex-end;
    }
    .bubble-right {
        background: linear-gradient(to right, #0084ff, #0099ff);
        color: white;
        padding: 10px 15px;
        border-radius: 18px 18px 4px 18px;
        max-width: 70%;
        font-size: 15px;
        box-shadow: 0 2px 5px rgba(0,132,255,0.2);
    }

    /* Tin nhắn người khác (Bên trái) */
    .msg-left {
        display: flex;
        justify-content: flex-start;
        margin-bottom: 8px;
        align-items: flex-end;
    }
    .bubble-left {
        background: #e4e6eb;
        color: #050505;
        padding: 10px 15px;
        border-radius: 18px 18px 18px 4px;
        max-width: 70%;
        font-size: 15px;
    }
    
    /* Avatar trong chat */
    .chat-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        margin-right: 8px;
        border: 1px solid #eee;
    }

    /* Thẻ cuộc gọi (Call Card) */
    .call-card {
        background: #e8f5e9;
        border: 1px solid #c8e6c9;
        border-radius: 10px;
        padding: 12px;
        display: flex;
        align-items: center;
        gap: 15px;
        width: fit-content;
    }
    .call-btn {
        background-color: #2e7d32;
        color: white !important;
        text-decoration: none;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 13px;
        border: none;
    }
    
    /* Nút bấm (Button) đẹp hơn */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: 0.2s;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. XỬ LÝ DATABASE & CÁC HÀM HỖ TRỢ (CORE LOGIC)
# ==============================================================================

# --- Kết nối Database an toàn ---
@st.cache_resource
def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

conn = get_db_connection()
cursor = conn.cursor()

# --- Khởi tạo Bảng dữ liệu (Chạy 1 lần) ---
def initialize_database():
    # 1. Bảng Người dùng
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
    
    # 2. Bảng Nơi làm việc (Chi nhánh)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workplaces (
            id TEXT PRIMARY KEY, 
            name TEXT, 
            created_by TEXT
        )
    ''')
    
    # 3. Bảng License Key (Bản quyền)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS license_keys (
            key_code TEXT PRIMARY KEY, 
            duration_days INTEGER, 
            status TEXT
        )
    ''')
    
    # 4. Bảng Tin nhắn Chat
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
    
    # 5. Bảng Phiên đăng nhập (Session)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, 
            username TEXT, 
            expiry TEXT
        )
    ''')
    conn.commit()

# Gọi hàm khởi tạo
initialize_database()

# Tài khoản Quản trị viên cấp cao (Hardcode)
SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

# --- Hàm Load Excel an toàn (Tránh lỗi thiếu file) ---
def load_excel_safe(file_path):
    # Các cột bắt buộc phải có
    required_columns = ["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]
    
    # Nếu file không tồn tại, trả về bảng rỗng
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=required_columns)
    
    try:
        df = pd.read_excel(file_path)
        # Kiểm tra và bù các cột còn thiếu
        for col in required_columns:
            if col not in df.columns:
                df[col] = "" # Tạo cột trống
        return df
    except:
        return pd.DataFrame(columns=required_columns)

# --- Hàm Lưu Excel an toàn (VÁ LỖI OSERROR) ---
def save_excel_safe(dataframe, file_path):
    # Lấy đường dẫn thư mục cha
    directory = os.path.dirname(file_path)
    
    # Nếu thư mục chưa tồn tại -> Tạo mới ngay lập tức
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        
    # Lưu file
    dataframe.to_excel(file_path, index=False)

# --- Hàm lấy Avatar ngẫu nhiên đẹp ---
def get_avatar_url(name):
    # Dùng dịch vụ DiceBear để tạo avatar dựa trên tên
    return f"https://api.dicebear.com/7.x/notionists/svg?seed={name}&backgroundColor=b6e3f4"

# --- Hàm xử lý Đăng nhập tự động (Session) ---
def create_login_session(username):
    token = str(uuid.uuid4())
    expiry_time = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, expiry_time))
    conn.commit()
    return token

def verify_session_token(token):
    try:
        cursor.execute("SELECT username, expiry FROM sessions WHERE token=?", (token,))
        row = cursor.fetchone()
        if row:
            expiry_str = row[1]
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
            if expiry_date > datetime.now():
                return row[0] # Trả về username nếu token còn hạn
    except:
        pass
    return None

# Kiểm tra Session ngay đầu chương trình
if "session" in st.query_params:
    token = st.query_params["session"]
    auto_user = verify_session_token(token)
    
    if auto_user and 'user' not in st.session_state:
        # Lấy thông tin user từ DB
        cursor.execute('SELECT * FROM users WHERE username=?', (auto_user,))
        user_data = cursor.fetchone()
        if user_data:
            st.session_state.user = user_data[0]
            st.session_state.role = user_data[2]
            st.session_state.zalo = user_data[4]
            st.session_state.wp_id = user_data[5]
            st.session_state.expiry = user_data[8]

# ==============================================================================
# 3. GIAO DIỆN CHAT REAL-TIME (SỬ DỤNG FRAGMENT ĐỂ MƯỢT)
# ==============================================================================
@st.fragment(run_every=2)
def render_chat_window(room_id, current_user_name, chat_mode="group"):
    try:
        # Lấy 50 tin nhắn mới nhất
        cursor.execute("SELECT sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,))
        messages = cursor.fetchall()[::-1] # Đảo ngược để tin mới nhất nằm dưới cùng
    except:
        return

    # Hiển thị tiêu đề phòng chat
    chat_icon = "🏢" if chat_mode == "group" else "💬"
    display_room_name = room_id if chat_mode == "group" else "Cuộc trò chuyện riêng tư"
    st.markdown(f"<div style='text-align:center; color:#888; font-size:12px; margin-bottom:10px;'>{chat_icon} {display_room_name}</div>", unsafe_allow_html=True)

    # Bắt đầu vẽ khung chat HTML
    html_content = '<div class="chat-container">'
    last_sender = None
    
    for sender, content, ts, msg_type in messages:
        is_me = (sender == current_user_name)
        
        # Mở thẻ div bao ngoài (Hàng)
        if is_me:
            html_content += '<div class="msg-right">'
        else:
            html_content += '<div class="msg-left">'
            # Nếu người gửi khác người trước đó -> Hiện avatar
            if sender != last_sender:
                avatar_url = get_avatar_url(sender)
                html_content += f'<img src="{avatar_url}" class="chat-avatar" title="{sender}">'
            else:
                html_content += '<div style="width:40px;"></div>' # Khoảng trống nếu cùng người gửi

        # Xử lý nội dung tin nhắn
        msg_body = ""
        
        # 1. Nếu là Ảnh
        if msg_type == 'image':
            import base64
            if os.path.exists(content):
                with open(content, "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode()
                msg_body = f'<img src="data:image/png;base64,{img_base64}" style="max-width:200px; border-radius:10px;">'
            else:
                msg_body = "<i>⚠️ Hình ảnh đã bị xóa</i>"
        
        # 2. Nếu là Emoji/Icon to
        elif msg_type == 'emoji':
            msg_body = f'<div style="font-size:36px; line-height:1;">{content}</div>'
            
        # 3. Nếu là Cuộc gọi (Call)
        elif msg_type == 'call':
            link = content.split('|')[-1]
            icon = "📹" if "video" in content else "📞"
            text_call = "Video Call" if "video" in content else "Voice Call"
            msg_body = f'''
            <div class="call-card">
                <div style="font-size:24px;">{icon}</div>
                <div>
                    <div style="font-weight:bold; font-size:13px; color:#2e7d32;">{sender} đang gọi...</div>
                    <div style="margin-top:5px;">
                        <a href="{link}" target="_blank" class="call-btn">Tham gia {text_call}</a>
                    </div>
                </div>
            </div>
            '''
            
        # 4. Nếu là Văn bản thường
        else:
            # Highlight Tag tên (@User)
            if f"@{current_user_name}" in content:
                content = f"<span style='background-color:#fff3cd; padding:2px 5px; border-radius:4px; font-weight:bold;'>{content}</span>"
            msg_body = content

        # Đóng gói vào bong bóng chat (Bubble)
        if msg_type == 'emoji' or msg_type == 'call':
            # Emoji và Call không cần nền màu
            html_content += f'<div>{msg_body}</div>'
        else:
            bubble_class = "bubble-right" if is_me else "bubble-left"
            # Thêm tên người gửi nếu là nhóm và không phải mình
            name_label = ""
            if chat_mode == "group" and not is_me and sender != last_sender:
                name_label = f"<div style='font-size:10px; color:#888; margin-bottom:2px; margin-left:5px;'>{sender}</div>"
            
            html_content += f'<div>{name_label}<div class="{bubble_class}" title="{ts}">{msg_body}</div></div>'

        html_content += '</div>' # Đóng thẻ Hàng
        last_sender = sender

    html_content += '</div>' # Đóng Container
    
    # Render HTML
    st.markdown(html_content, unsafe_allow_html=True)
    
    # Javascript để tự động cuộn xuống cuối
    st.markdown("""
        <script>
            var chatDiv = window.parent.document.querySelector('.chat-container');
            if (chatDiv) {
                chatDiv.scrollTop = chatDiv.scrollHeight;
            }
        </script>
    """, unsafe_allow_html=True)

# --- Fragment Dashboard (Thống kê) ---
@st.fragment
def render_dashboard(staff_list):
    if not staff_list:
        st.warning("Chưa có dữ liệu nhân viên.")
        return

    total_debt = 0
    staff_count = len(staff_list)
    alert_count = 0
    today = datetime.now().strftime("%Y-%m-%d")

    for staff in staff_list:
        staff_id = staff[0]
        file_path = os.path.join(STORAGE_DIR, staff_id, "salary.xlsx")
        df = load_excel_safe(file_path)
        
        # Tính tổng nợ
        if "Trạng thái" in df.columns and "Tổng lương" in df.columns:
            debt = pd.to_numeric(df[df["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
            total_debt += debt
            
        # Đếm ca làm hôm nay
        if "Ngày" in df.columns:
            shifts_today = df[df["Ngày"].astype(str).str.contains(today, na=False)]
            if not shifts_today.empty:
                alert_count += 1

    # Hiển thị 3 Card thống kê
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{staff_count}</div><div class="metric-label">Nhân sự</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{total_debt:,.0f}</div><div class="metric-label">Tổng Nợ Lương (VNĐ)</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{alert_count}</div><div class="metric-label">Nhân viên đi làm hôm nay</div></div>""", unsafe_allow_html=True)
    
    st.write("") # Khoảng cách

# ==============================================================================
# 4. LUỒNG ĐĂNG NHẬP / ĐĂNG KÝ (AUTHENTICATION)
# ==============================================================================
if 'user' not in st.session_state:
    col_spacer1, col_center, col_spacer2 = st.columns([1, 2, 1])
    
    with col_center:
        st.markdown("<h1 style='text-align: center; color: #1877f2;'>🌐 HỆ THỐNG V31 ULTIMATE</h1>", unsafe_allow_html=True)
        
        tab_login, tab_register, tab_super = st.tabs(["Đăng Nhập", "Đăng Ký Mới", "Super Admin"])
        
        # --- TAB SUPER ADMIN ---
        with tab_super:
            st.warning("Khu vực dành cho Quản trị viên cấp cao")
            sa_user = st.text_input("Super User")
            sa_pass = st.text_input("Super Password", type="password")
            
            if st.button("🚀 Truy Cập Hệ Thống Gốc", use_container_width=True):
                if sa_user == SUPER_ADMIN_USER and sa_pass == SUPER_ADMIN_PASS:
                    st.session_state.user = "SUPER_ADMIN"
                    st.session_state.role = "super_admin"
                    st.rerun()
                else:
                    st.error("Sai thông tin đăng nhập!")

        # --- TAB ĐĂNG NHẬP ---
        with tab_login:
            login_user = st.text_input("Tên đăng nhập")
            login_pass = st.text_input("Mật khẩu", type="password")
            
            if st.button("Đăng nhập", type="primary", use_container_width=True):
                cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (login_user, login_pass))
                user_data = cursor.fetchone()
                
                if user_data:
                    # Lưu session state
                    st.session_state.user = user_data[0]
                    st.session_state.role = user_data[2]
                    st.session_state.zalo = user_data[4]
                    st.session_state.wp_id = user_data[5]
                    st.session_state.expiry = user_data[8]
                    
                    # Tạo token cookie giả lập
                    new_token = create_login_session(user_data[0])
                    st.query_params["session"] = new_token
                    
                    st.success(f"Chào mừng {user_data[4]} quay trở lại!")
                    st.rerun()
                else:
                    st.error("Sai tên đăng nhập hoặc mật khẩu.")

        # --- TAB ĐĂNG KÝ ---
        with tab_register:
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                reg_user = st.text_input("Tên đăng nhập (ID)", key="reg_u")
                reg_name = st.text_input("Tên hiển thị (Zalo)", key="reg_n")
                reg_phone = st.text_input("Số điện thoại", key="reg_p")
            with col_r2:
                reg_pass = st.text_input("Mật khẩu", type="password", key="reg_pass")
                reg_role = st.radio("Vai trò:", ["Nhân viên", "Quản lý"], horizontal=True)
                
                reg_wp = "ADMIN"
                if reg_role == "Nhân viên":
                    reg_wp = st.text_input("Nhập Mã Chi Nhánh (Hỏi quản lý)")
            
            if st.button("Tạo Tài Khoản Mới", use_container_width=True):
                if not reg_user or not reg_pass or not reg_name:
                    st.warning("Vui lòng điền đầy đủ thông tin.")
                else:
                    try:
                        # Validate Mã chi nhánh
                        if reg_role == "Nhân viên":
                            cursor.execute("SELECT id FROM workplaces WHERE id=?", (reg_wp,))
                            if not cursor.fetchone():
                                st.error("❌ Mã Chi Nhánh không tồn tại!")
                                st.stop()
                        
                        # Thêm vào DB
                        cursor.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', 
                                       (reg_user, reg_pass, 'admin' if reg_role=="Quản lý" else 'staff', 
                                        None, reg_name, reg_wp, reg_phone, None, "2099-01-01"))
                        conn.commit()
                        st.success("✅ Đăng ký thành công! Vui lòng chuyển sang Tab Đăng nhập.")
                    except sqlite3.IntegrityError:
                        st.error("❌ Tên đăng nhập này đã được sử dụng.")

    st.stop() # Dừng không chạy phần dưới nếu chưa login

# ==============================================================================
# 5. MÀN HÌNH CHÍNH (SAU KHI ĐĂNG NHẬP THÀNH CÔNG)
# ==============================================================================
current_user = st.session_state.user
current_role = st.session_state.role
current_zalo = st.session_state.zalo if 'zalo' in st.session_state else current_user
current_wp_id = st.session_state.wp_id if 'wp_id' in st.session_state else ""

# --- SIDEBAR (THANH BÊN TRÁI) ---
with st.sidebar:
    st.image(get_avatar_url(current_zalo), width=100)
    st.title(current_zalo)
    st.caption(f"ID: {current_user}")
    st.caption(f"Chức vụ: {current_role}")
    if current_wp_id and current_wp_id != "ADMIN":
        st.caption(f"Chi nhánh: {current_wp_id}")
    
    st.divider()
    
    if st.button("🚪 Đăng xuất an toàn", use_container_width=True):
        if "session" in st.query_params:
            cursor.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],))
            conn.commit()
            st.query_params.clear()
        del st.session_state.user
        st.rerun()

# --- KHU VỰC SUPER ADMIN (QUẢN TRỊ CAO CẤP) ---
if current_role == 'super_admin':
    st.header("🔧 SUPER ADMIN DASHBOARD")
    
    tab_keys, tab_reset = st.tabs(["Quản Lý Key", "⚡ Reset Hệ Thống"])
    
    with tab_keys:
        st.write("Tạo mã kích hoạt cho Quản lý:")
        key_type = st.selectbox("Loại Key", ["30 Ngày", "365 Ngày", "Vĩnh viễn"])
        if st.button("Sinh Key Mới"):
            new_key = str(uuid.uuid4())[:8].upper()
            days = 36500 if key_type == "Vĩnh viễn" else (365 if key_type == "365 Ngày" else 30)
            cursor.execute("INSERT INTO license_keys VALUES (?,?,?)", (new_key, days, "active"))
            conn.commit()
            st.success(f"Key vừa tạo: **{new_key}**")
        
        # Xem danh sách key
        keys_df = pd.read_sql_query("SELECT * FROM license_keys", conn)
        st.dataframe(keys_df)

    with tab_reset:
        st.error("⚠️ Cảnh báo: Hành động này sẽ xóa sạch dữ liệu!")
        if st.button("💣 XÓA TOÀN BỘ DATABASE & LÀM LẠI TỪ ĐẦU"):
            st.cache_resource.clear()
            cursor.close()
            conn.close()
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            st.success("Đã xóa sạch hệ thống. Vui lòng nhấn F5 (Tải lại trang) ngay bây giờ.")
    
    st.stop() # Dừng code

# --- KIỂM TRA BẢN QUYỀN (CHO ADMIN) ---
if current_role == 'admin':
    expiry_date_str = st.session_state.expiry or "2000-01-01"
    days_left = (datetime.strptime(expiry_date_str, "%Y-%m-%d") - datetime.now()).days
    
    if days_left < 0:
        st.error(f"🔒 TÀI KHOẢN HẾT HẠN! (Quá hạn {-days_left} ngày)")
        key_input = st.text_input("Nhập License Key để gia hạn:")
        if st.button("Kích hoạt"):
            key_data = cursor.execute("SELECT duration_days FROM license_keys WHERE key_code=? AND status='active'", (key_input,)).fetchone()
            if key_data:
                new_expiry = (datetime.now() + timedelta(days=key_data[0])).strftime("%Y-%m-%d")
                cursor.execute("UPDATE users SET expiry_date=? WHERE username=?", (new_expiry, current_user))
                cursor.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (key_input,))
                conn.commit()
                st.session_state.expiry = new_expiry
                st.success("Kích hoạt thành công! Vui lòng đợi...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Mã Key không hợp lệ hoặc đã sử dụng.")
        st.stop()
    else:
        st.sidebar.success(f"✅ Bản quyền: Còn {days_left} ngày")

# --- NỘI DUNG CHÍNH (TABS) ---
tab_comms, tab_manage = st.tabs(["💬 Trung Tâm Liên Lạc", "📊 Quản Lý & Công Việc"])

# === TAB 1: CHAT ===
with tab_comms:
    chat_mode_select = st.radio("", ["🏢 Nhóm Chung", "👤 Nhắn Riêng"], horizontal=True, label_visibility="collapsed")
    
    active_room_id = None
    
    # 1. Chọn Phòng Chat
    if chat_mode_select == "🏢 Nhóm Chung":
        if current_role == 'admin':
            # Admin thấy tất cả nhóm
            rooms_data = cursor.execute("SELECT id FROM workplaces").fetchall()
            rooms_list = [r[0] for r in rooms_data]
            if rooms_list:
                active_room_id = st.selectbox("Chọn Chi nhánh:", rooms_list)
            else:
                st.info("Chưa có chi nhánh nào. Vui lòng tạo bên tab Quản lý.")
        else:
            # Nhân viên chỉ thấy nhóm mình
            active_room_id = current_wp_id
            
    else: # Nhắn riêng
        # Lấy danh sách user khác mình
        users_data = cursor.execute("SELECT zalo_name FROM users WHERE username != ?", (current_user,)).fetchall()
        users_list = [u[0] for u in users_data]
        
        if users_list:
            target_user_name = st.selectbox("Chọn người muốn nhắn:", users_list)
            # Tạo Room ID duy nhất cho cặp đôi
            user_pair = sorted([current_zalo, target_user_name])
            active_room_id = f"DM_{user_pair[0]}_{user_pair[1]}"
        else:
            st.info("Chưa có ai khác trong hệ thống.")

    # 2. Hiển thị Chat
    if active_room_id:
        render_chat_window(active_room_id, current_zalo, "group" if chat_mode_select == "🏢 Nhóm Chung" else "private")
        
        # 3. Input Gửi tin
        col_chat_input, col_chat_tools = st.columns([6, 1])
        
        with col_chat_input:
            msg_input = st.chat_input("Nhập tin nhắn... (Gõ @Tên để nhắc)")
            if msg_input:
                ts_now = datetime.now().strftime("%H:%M")
                cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", 
                               (active_room_id, current_zalo, msg_input, ts_now, "text"))
                conn.commit()
                # Không cần rerun để trải nghiệm mượt hơn
        
        with col_chat_tools:
            with st.popover("➕", use_container_width=True):
                st.write("**Tiện ích:**")
                
                # Nút gọi Video
                if st.button("📹 Video Call", use_container_width=True):
                    call_link = f"https://meet.jit.si/call_{uuid.uuid4()}"
                    ts_now = datetime.now().strftime("%H:%M")
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                   (active_room_id, current_zalo, f"video|{call_link}", ts_now, "call"))
                    conn.commit()
                    st.rerun()
                
                st.divider()
                st.write("**Gửi ảnh:**")
                uploaded_img = st.file_uploader("", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
                if uploaded_img and st.button("Gửi Ảnh", use_container_width=True):
                    # Lưu file ảnh
                    file_ext = uploaded_img.name.split('.')[-1]
                    file_name = f"{uuid.uuid4()}.{file_ext}"
                    file_path = os.path.join(UPLOAD_DIR, file_name)
                    
                    with open(file_path, "wb") as f:
                        f.write(uploaded_img.getbuffer())
                    
                    ts_now = datetime.now().strftime("%H:%M")
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                   (active_room_id, current_zalo, file_path, ts_now, "image"))
                    conn.commit()
                    st.rerun()

# === TAB 2: QUẢN LÝ CÔNG VIỆC ===
with tab_manage:
    # ---------------------------
    # GIAO DIỆN ADMIN (QUẢN LÝ)
    # ---------------------------
    if current_role == 'admin':
        # Phần Cấu hình
        with st.expander("⚙️ CẤU HÌNH CHI NHÁNH MỚI"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                new_wp_id = st.text_input("Mã Chi Nhánh (VD: Q1)").upper()
            with col_c2:
                new_wp_name = st.text_input("Tên hiển thị (VD: Cafe Quận 1)")
                
            if st.button("Tạo Chi Nhánh"):
                try:
                    cursor.execute("INSERT INTO workplaces VALUES (?,?,?)", (new_wp_id, new_wp_name, current_user))
                    conn.commit()
                    st.success(f"Đã tạo thành công: {new_wp_name}")
                    time.sleep(1)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Mã chi nhánh này đã tồn tại.")
        
        # Dashboard Thống kê
        staff_list = cursor.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        render_dashboard(staff_list)
        
        # Quản lý từng nhân viên
        if staff_list:
            st.divider()
            st.subheader("📝 Bảng Lương & Chấm Công")
            
            # Chọn nhân viên
            staff_options = [f"{s[1]} ({s[0]})" for s in staff_list]
            selected_staff_label = st.selectbox("Chọn nhân viên:", staff_options)
            
            if selected_staff_label:
                # Lấy ID nhân viên từ chuỗi "Tên (ID)"
                target_id = selected_staff_label.split('(')[1].replace(')', '')
                
                # Đường dẫn file lương của nhân viên đó
                target_file = os.path.join(STORAGE_DIR, target_id, "salary.xlsx")
                df_salary = load_excel_safe(target_file)
                
                # Tính toán nợ lương
                current_debt = 0
                if "Trạng thái" in df_salary.columns and "Tổng lương" in df_salary.columns:
                    # Lọc các dòng có trạng thái chứa chữ "chưa"
                    unpaid_rows = df_salary[df_salary["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]
                    current_debt = pd.to_numeric(unpaid_rows["Tổng lương"], errors='coerce').sum()
                
                col_info1, col_info2 = st.columns([2, 1])
                with col_info1:
                    st.metric("Tổng tiền đang nợ nhân viên:", f"{current_debt:,.0f} VNĐ")
                
                with col_info2:
                    if current_debt > 0:
                        if st.button("💸 Thanh Toán Ngay", use_container_width=True):
                            # Cập nhật trạng thái trong Excel
                            mask = df_salary["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)
                            df_salary.loc[mask, "Trạng thái"] = "đã nhận"
                            
                            save_excel_safe(df_salary, target_file)
                            
                            # Gửi thông báo vào Chat
                            target_wp = [s[2] for s in staff_list if s[0] == target_id][0]
                            msg = f"✅ Đã thanh toán lương: {current_debt:,.0f} VNĐ"
                            ts = datetime.now().strftime("%H:%M")
                            cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                           (target_wp, current_zalo, msg, ts, "text"))
                            conn.commit()
                            
                            st.success("Đã thanh toán!")
                            time.sleep(1)
                            st.rerun()
                
                # Form thêm ca làm việc
                with st.expander("➕ Thêm Ca Làm Việc Thủ Công"):
                    with st.form("admin_add_shift_form"):
                        col_f1, col_f2 = st.columns(2)
                        with col_f1:
                            input_date = st.date_input("Ngày làm", datetime.now())
                            input_loc = st.text_input("Vị trí", "Tại quán")
                        with col_f2:
                            input_in = st.time_input("Giờ vào")
                            input_out = st.time_input("Giờ ra")
                        
                        input_rate = st.number_input("Lương theo giờ (VNĐ)", value=20000)
                        
                        if st.form_submit_button("Lưu Ca Làm", use_container_width=True):
                            # Tính toán giờ làm
                            dt_in = datetime.combine(input_date, input_in)
                            dt_out = datetime.combine(input_date, input_out)
                            
                            # Nếu giờ ra nhỏ hơn giờ vào -> coi như qua đêm (thêm 1 ngày)
                            if dt_out < dt_in:
                                dt_out += timedelta(days=1)
                            
                            hours_worked = (dt_out - dt_in).total_seconds() / 3600
                            total_pay = hours_worked * input_rate
                            
                            # Tạo dòng dữ liệu mới
                            new_record = pd.DataFrame([{
                                "Ngày": input_date.strftime("%Y-%m-%d"),
                                "Vị trí": input_loc,
                                "Giờ vào": input_in.strftime("%H:%M"),
                                "Giờ ra": input_out.strftime("%H:%M"),
                                "Tổng lương": total_pay,
                                "Trạng thái": "chưa nhận",
                                "Xác nhận đến": False
                            }])
                            
                            # Gộp vào bảng cũ
                            df_salary = pd.concat([df_salary, new_record], ignore_index=True)
                            
                            # Lưu file an toàn
                            save_excel_safe(df_salary, target_file)
                            
                            st.success("Đã thêm ca thành công!")
                            st.rerun()
                
                # Hiển thị bảng lương
                st.dataframe(df_salary, use_container_width=True)

    # ---------------------------
    # GIAO DIỆN NHÂN VIÊN (STAFF)
    # ---------------------------
    elif current_role == 'staff':
        # File lương của chính mình
        my_salary_file = os.path.join(STORAGE_DIR, current_user, "salary.xlsx")
        df_my_salary = load_excel_safe(my_salary_file)
        
        # Tính nợ
        my_debt = 0
        if "Trạng thái" in df_my_salary.columns and "Tổng lương" in df_my_salary.columns:
            my_debt = pd.to_numeric(df_my_salary[df_my_salary["Trạng thái"].astype(str).str.lower().str.contains("chưa", na=False)]["Tổng lương"], errors='coerce').sum()
        
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            st.metric("💰 Tổng tiền quán đang nợ bạn:", f"{my_debt:,.0f} VNĐ")
        with col_s2:
            if my_debt > 0:
                if st.button("🔔 Nhắc Quản lý trả tiền", use_container_width=True):
                    msg = f"📣 @Quản_lý ơi! Check lương giúp em với: {my_debt:,.0f} VNĐ"
                    ts = datetime.now().strftime("%H:%M")
                    cursor.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", 
                                   (current_wp_id, current_zalo, msg, ts, "text"))
                    conn.commit()
                    st.toast("Đã gửi tin nhắn nhắc nhở!", icon="🚀")
        
        st.divider()
        
        # Form tự báo cáo
        with st.expander("➕ Báo cáo ca làm việc", expanded=True):
            with st.form("staff_report_form"):
                col_sf1, col_sf2 = st.columns(2)
                with col_sf1:
                    s_date = st.date_input("Ngày")
                    s_loc = st.text_input("Vị trí", current_wp_id)
                with col_sf2:
                    s_in = st.time_input("Giờ vào")
                    s_out = st.time_input("Giờ ra")
                
                if st.form_submit_button("Gửi báo cáo", use_container_width=True):
                    dt_s_in = datetime.combine(s_date, s_in)
                    dt_s_out = datetime.combine(s_date, s_out)
                    if dt_s_out < dt_s_in:
                        dt_s_out += timedelta(days=1)
                    
                    h_worked = (dt_s_out - dt_s_in).total_seconds() / 3600
                    # Lương mặc định 20k, quản lý có thể sửa sau
                    estimated_pay = h_worked * 20000 
                    
                    new_rec = pd.DataFrame([{
                        "Ngày": s_date.strftime("%Y-%m-%d"),
                        "Vị trí": s_loc,
                        "Giờ vào": s_in.strftime("%H:%M"),
                        "Giờ ra": s_out.strftime("%H:%M"),
                        "Tổng lương": estimated_pay,
                        "Trạng thái": "chưa nhận",
                        "Xác nhận đến": False
                    }])
                    
                    df_my_salary = pd.concat([df_my_salary, new_rec], ignore_index=True)
                    
                    # Lưu an toàn (Tự tạo thư mục nếu chưa có)
                    save_excel_safe(df_my_salary, my_salary_file)
                    
                    st.success("Đã lưu báo cáo!")
                    st.rerun()
        
        st.dataframe(df_my_salary, use_container_width=True)