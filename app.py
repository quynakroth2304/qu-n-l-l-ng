import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
import shutil
from datetime import datetime, timedelta

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG V44 (ENHANCED UX)
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống Quản Lý V44", 
    layout="wide", 
    page_icon="🛡️", 
    initial_sidebar_state="expanded"
)

# --- THIẾT LẬP DATABASE VÀ THƯ MỤC ---
DATABASE_FILE = "system_v44_stable.db"
STORAGE_DIRECTORY = "user_files"
UPLOAD_DIRECTORY = "chat_uploads"

# Tự động tạo thư mục nếu chưa tồn tại
if not os.path.exists(STORAGE_DIRECTORY):
    os.makedirs(STORAGE_DIRECTORY)
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

# --- CSS GIAO DIỆN NÂNG CAP (MESSENGER/ZALO STYLE) ---
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

    /* KHUNG CHAT MỚI - GIỐNG MESSENGER/ZALO */
    .chat-container {
        padding: 16px;
        background: #ffffff;
        border-radius: 16px;
        height: 75vh;
        overflow-y: auto;
        border: 1px solid #e2e8f0;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    /* CUSTOM SCROLLBAR */
    .chat-container::-webkit-scrollbar {
        width: 6px;
    }
    .chat-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    .chat-container::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 10px;
    }
    .chat-container::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }
    
    /* MESSAGE ROW - INLINE FLEX */
    .message-row {
        display: flex;
        align-items: flex-end;
        margin-bottom: 4px;
        width: 100%;
        gap: 8px;
    }

    /* Tin nhắn bên PHẢI (Admin/Người gửi) */
    .message-right {
        justify-content: flex-end;
    }
    .bubble-right {
        background: linear-gradient(135deg, #0084ff 0%, #0066cc 100%);
        color: white;
        padding: 10px 14px;
        border-radius: 18px 18px 4px 18px;
        max-width: 65%;
        word-wrap: break-word;
        white-space: pre-wrap;
        font-size: 14.5px;
        line-height: 1.4;
        box-shadow: 0 1px 2px rgba(0,132,255,0.25);
        animation: slideInRight 0.3s ease-out;
    }

    /* Tin nhắn bên TRÁI (Nhân viên/Người nhận) */
    .message-left {
        justify-content: flex-start;
    }
    .bubble-left {
        background: #e4e6eb;
        color: #050505;
        padding: 10px 14px;
        border-radius: 18px 18px 18px 4px;
        max-width: 65%;
        word-wrap: break-word;
        white-space: pre-wrap;
        font-size: 14.5px;
        line-height: 1.4;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        animation: slideInLeft 0.3s ease-out;
    }
    
    /* AVATAR */
    .chat-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        object-fit: cover;
        flex-shrink: 0;
    }
    
    /* TIMESTAMP */
    .message-time {
        font-size: 11px;
        color: #65676b;
        margin-top: 2px;
        text-align: center;
    }
    
    /* NÚT XÁC NHẬN THANH TOÁN - INLINE */
    .payment-confirm-btn {
        display: inline-block;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        text-align: center;
        cursor: pointer;
        margin-top: 6px;
        box-shadow: 0 2px 6px rgba(16,185,129,0.3);
        transition: all 0.2s;
        border: none;
        text-decoration: none;
    }
    .payment-confirm-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(16,185,129,0.4);
    }
    
    .payment-confirmed {
        display: inline-block;
        background: #e0e0e0;
        color: #666;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        margin-top: 6px;
        font-style: italic;
    }

    /* ANIMATIONS */
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    /* Nút bấm (Button) */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        border: none;
        padding: 0.6rem 1.2rem;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* INPUT FIELD */
    .stChatInput {
        border-radius: 24px !important;
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
            ban_until TEXT
        )
    ''')
    
    # Bảng Chi nhánh
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workplaces (
            workplace_id TEXT PRIMARY KEY, 
            display_name TEXT, 
            created_by TEXT
        )
    ''')
    
    # Bảng Tin nhắn - THÊM CỘT payment_confirmed
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            workplace_id TEXT, 
            sender TEXT, 
            content TEXT, 
            timestamp TEXT, 
            msg_type TEXT,
            payment_confirmed INTEGER DEFAULT 0
        )
    ''')
    
    connection.commit()

initialize_database_tables()

# ==============================================================================
# 3. HÀM TỰ TẠO TÀI KHOẢN ADMIN NẾU CHƯA CÓ
# ==============================================================================
def ensure_admin_exists():
    existing_admin = cursor.execute("SELECT * FROM users WHERE role='admin' LIMIT 1").fetchone()
    if not existing_admin:
        cursor.execute("""
            INSERT INTO users (username, password, role, qr_path, zalo_name, workplace_id, phone) 
            VALUES (?, ?, 'admin', '', 'Admin Hệ Thống', 'HQ', '')
        """, ('admin', 'admin123'))
        connection.commit()

ensure_admin_exists()

# ==============================================================================
# 4. HÀM XỬ LÝ EXCEL (LOAD/SAVE AN TOÀN)
# ==============================================================================
def load_excel_safe(file_path):
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    else:
        return pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"])

def save_excel_safe(df, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_excel(file_path, index=False)

# ==============================================================================
# 5. GIAO DIỆN ĐĂNG NHẬP
# ==============================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align:center; color:#0ea5e9;'>🔐 ĐĂNG NHẬP HỆ THỐNG</h1>", unsafe_allow_html=True)
    col_left, col_center, col_right = st.columns([1, 2, 1])
    
    with col_center:
        with st.form("login_form", clear_on_submit=True):
            username_input = st.text_input("👤 Tên đăng nhập", placeholder="Nhập username...")
            password_input = st.text_input("🔑 Mật khẩu", type="password", placeholder="Nhập password...")
            submit_btn = st.form_submit_button("🚀 Đăng nhập", use_container_width=True)
            
            if submit_btn:
                user_data = cursor.execute(
                    "SELECT * FROM users WHERE username=? AND password=?", 
                    (username_input, password_input)
                ).fetchone()
                
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.current_user = user_data[0]
                    st.session_state.current_role = user_data[2]
                    st.session_state.current_zalo = user_data[4]
                    st.session_state.current_workplace = user_data[5]
                    st.rerun()
                else:
                    st.error("❌ Sai tên đăng nhập hoặc mật khẩu!")
    st.stop()

# ==============================================================================
# 6. GIAO DIỆN CHÍNH (SAU KHI ĐĂNG NHẬP)
# ==============================================================================
current_user = st.session_state.current_user
current_role = st.session_state.current_role
current_zalo = st.session_state.current_zalo
current_workplace = st.session_state.current_workplace

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150/0ea5e9/ffffff?text=LOGO", width=120)
    st.markdown(f"### 👋 Xin chào, **{current_zalo}**")
    st.caption(f"🏢 Chi nhánh: **{current_workplace}**")
    st.caption(f"🎭 Vai trò: **{current_role.upper()}**")
    
    if st.button("🚪 Đăng xuất", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# ==============================================================================
# 7. HÀM DASHBOARD (ADMIN)
# ==============================================================================
def render_dashboard(staff_list):
    st.subheader("📊 DASHBOARD TỔNG QUAN")
    
    total_staff = len(staff_list)
    total_debt = 0
    pending_approvals = 0
    
    for staff in staff_list:
        staff_user = staff[0]
        salary_file = os.path.join(STORAGE_DIRECTORY, staff_user, "salary.xlsx")
        df = load_excel_safe(salary_file)
        
        pending_approvals += len(df[df["Xác nhận đến"].astype(str).str.lower() == "false"])
        unpaid_mask = ~df["Trạng thái"].astype(str).str.lower().str.contains("đã nhận", na=False)
        total_debt += pd.to_numeric(df[unpaid_mask]["Tổng lương"], errors='coerce').sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_staff}</div>
            <div class="metric-label">Tổng Nhân Viên</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:#f59e0b;">{pending_approvals}</div>
            <div class="metric-label">Ca Chờ Duyệt</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:#ef4444;">{total_debt:,.0f} đ</div>
            <div class="metric-label">Tổng Nợ Lương</div>
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# 8. TABS CHÍNH
# ==============================================================================
tab_chat, tab_tasks = st.tabs(["💬 CHAT", "📋 CÔNG VIỆC"])

# === TAB 1: CHAT (CẢI TIẾN) ===
with tab_chat:
    st.subheader("💬 Hệ Thống Chat")
    
    # Lấy danh sách phòng chat
    if current_role == 'admin':
        chat_rooms = cursor.execute("SELECT DISTINCT workplace_id FROM messages ORDER BY id DESC").fetchall()
    else:
        chat_rooms = [(current_workplace,)]
    
    if chat_rooms:
        active_room_id = st.selectbox("🏢 Chọn chi nhánh:", [r[0] for r in chat_rooms], label_visibility="collapsed")
        
        # Hiển thị tin nhắn
        messages = cursor.execute(
            "SELECT sender, content, timestamp, msg_type, id, payment_confirmed FROM messages WHERE workplace_id=? ORDER BY id", 
            (active_room_id,)
        ).fetchall()
        
        chat_html = '<div class="chat-container">'
        for msg in messages:
            sender_name, content, time_str, msg_type, msg_id, payment_confirmed = msg
            is_me = (sender_name == current_zalo)
            
            if msg_type == "text":
                # Kiểm tra nếu là tin nhắn chuyển khoản từ admin
                is_payment_msg = ("chuyển khoản" in content.lower() or "chuyển tiền" in content.lower())
                
                if is_me:
                    chat_html += f'''
                    <div class="message-row message-right">
                        <div>
                            <div class="bubble-right">{content}</div>
                            <div class="message-time">{time_str}</div>
                        </div>
                    </div>
                    '''
                else:
                    confirm_btn = ""
                    if is_payment_msg and current_role == 'staff' and payment_confirmed == 0:
                        confirm_btn = f'''
                        <div style="text-align: left;">
                            <button class="payment-confirm-btn" onclick="window.location.href='?confirm_payment={msg_id}'">
                                ✅ Xác nhận đã nhận tiền
                            </button>
                        </div>
                        '''
                    elif is_payment_msg and payment_confirmed == 1:
                        confirm_btn = '<div class="payment-confirmed">✓ Đã xác nhận</div>'
                    
                    chat_html += f'''
                    <div class="message-row message-left">
                        <img src="https://ui-avatars.com/api/?name={sender_name}&background=0ea5e9&color=fff" class="chat-avatar"/>
                        <div>
                            <div class="bubble-left">{content}</div>
                            {confirm_btn}
                            <div class="message-time">{time_str}</div>
                        </div>
                    </div>
                    '''
            
            elif msg_type == "image":
                img_side = "right" if is_me else "left"
                chat_html += f'''
                <div class="message-row message-{img_side}">
                    {'' if is_me else f'<img src="https://ui-avatars.com/api/?name={sender_name}&background=0ea5e9&color=fff" class="chat-avatar"/>'}
                    <div>
                        <img src="{content}" style="max-width: 250px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);"/>
                        <div class="message-time">{time_str}</div>
                    </div>
                </div>
                '''
            
            elif msg_type == "call":
                call_link = content.split('|')[1]
                chat_html += f'''
                <div class="message-row message-right">
                    <div class="bubble-right">
                        📹 <a href="{call_link}" target="_blank" style="color:white; text-decoration: underline;">Tham gia cuộc gọi</a>
                    </div>
                </div>
                '''
        
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)
        
        # XỬ LÝ XÁC NHẬN THANH TOÁN
        query_params = st.query_params
        if "confirm_payment" in query_params:
            msg_id_to_confirm = query_params["confirm_payment"]
            
            # Cập nhật trạng thái tin nhắn
            cursor.execute("UPDATE messages SET payment_confirmed=1 WHERE id=?", (msg_id_to_confirm,))
            connection.commit()
            
            # Cập nhật Excel
            my_file_path = os.path.join(STORAGE_DIRECTORY, current_user, "salary.xlsx")
            df_my_salary = load_excel_safe(my_file_path)
            df_my_salary.loc[df_my_salary["Trạng thái"].astype(str).str.lower() == "chờ xác nhận", "Trạng thái"] = "đã nhận"
            save_excel_safe(df_my_salary, my_file_path)
            
            # Gửi tin phản hồi
            cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", 
                          (active_room_id, current_zalo, "✅ Em đã nhận được tiền lương rồi ạ!", datetime.now().strftime("%H:%M"), "text"))
            connection.commit()
            
            # Xóa query param và reload
            st.query_params.clear()
            st.rerun()
        
        # Input tin nhắn
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        column_input, column_tools = st.columns([6, 1])
        with column_input:
            message_input = st.chat_input("Nhập tin nhắn...")
            if message_input:
                cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", 
                               (active_room_id, current_zalo, message_input, datetime.now().strftime("%H:%M"), "text"))
                connection.commit()
                st.rerun()
        
        with column_tools:
            with st.popover("➕", use_container_width=True):
                if st.button("📹 Call Video", use_container_width=True):
                    call_link = f"https://meet.jit.si/call_{uuid.uuid4()}"
                    cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", 
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
                    
                    cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", 
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
                        st.success("✅ Thành công!")
                        st.rerun()
                    except:
                        st.error("❌ Mã này đã tồn tại.")
            with list_tab:
                my_branches = pd.read_sql_query(f"SELECT * FROM workplaces WHERE created_by='{current_user}'", connection)
                st.dataframe(my_branches, use_container_width=True)

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
            
            st.info(f"📞 Liên hệ: {staff_list[[s[0] for s in staff_list].index(target_id)][3]}")
            
            col_action1, col_action2, col_action3 = st.columns(3)
            with col_action1: st.metric("💰 Nợ lương:", f"{current_debt:,.0f} VNĐ")
            with col_action2: st.metric("⏳ Ca chưa duyệt:", f"{pending_shifts_count}")
            
            with col_action3:
                # Nút Duyệt chấm công
                if pending_shifts_count > 0:
                    if st.button("✅ DUYỆT CHẤM CÔNG", use_container_width=True):
                        df_salary.loc[df_salary["Xác nhận đến"].astype(str).str.lower() == "false", "Xác nhận đến"] = True
                        save_excel_safe(df_salary, target_file_path)
                        st.success("✅ Đã duyệt thành công!")
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
                        cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", 
                                       (target_wp, current_zalo, f"🔔 Đã chuyển khoản lương: {current_debt:,.0f} VNĐ. Vui lòng xác nhận!", datetime.now().strftime("%H:%M"), "text"))
                        connection.commit()
                        st.success("✅ Đã gửi thông báo cho nhân viên!")
                        st.rerun()
            
            with st.expander("➕ Thêm Ca Làm Việc (Admin)"):
                with st.form("admin_add_shift"):
                    d = st.date_input("Ngày"); v = st.text_input("Vị trí", "Tại quán")
                    t1 = st.time_input("Vào"); t2 = st.time_input("Ra")
                    r = st.number_input("Lương/h (VNĐ)", value=20000, step=1000)
                    
                    if st.form_submit_button("💾 Lưu Ca", use_container_width=True):
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
                        st.success("✅ Đã thêm ca thành công!")
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
                st.info("💵 Quản lý đã báo chuyển tiền! Hãy kiểm tra và xác nhận trong phần Chat.")
            elif my_debt > 0:
                if st.button("🔔 Nhắc Quản lý", use_container_width=True):
                    cursor.execute("INSERT INTO messages (workplace_id, sender, content, timestamp, msg_type) VALUES (?,?,?,?,?)", 
                                   (current_workplace, current_zalo, f"📣 Anh/Chị ơi check lương giúp em: {my_debt:,.0f} VNĐ", datetime.now().strftime("%H:%M"), "text"))
                    connection.commit()
                    st.toast("✅ Đã gửi tin nhắn nhắc nhở!")
        
        with st.expander("➕ Báo cáo ca làm việc", expanded=True):
            with st.form("staff_add_shift"):
                d = st.date_input("Ngày"); v = st.text_input("Vị trí", current_workplace)
                t1 = st.time_input("Vào"); t2 = st.time_input("Ra")
                sr = st.number_input("Mức lương/giờ (VNĐ)", value=20000, step=1000)
                
                if st.form_submit_button("📤 Gửi báo cáo", use_container_width=True):
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
                    st.success("✅ Đã lưu báo cáo! Vui lòng chờ quản lý duyệt.")
                    st.rerun()
        
        st.dataframe(df_my_salary, use_container_width=True)