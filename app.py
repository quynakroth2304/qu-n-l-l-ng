import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
from datetime import datetime, timedelta

# --- 1. CẤU HÌNH & CSS FIX LỖI ---
st.set_page_config(page_title="System V63", layout="wide", page_icon="🛡️", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    
    /* --- NỀN TẢNG --- */
    .stApp { background-color: #18191a; font-family: 'Segoe UI', sans-serif; color: #e4e6eb; }
    
    /* Ẩn Header mặc định */
    header, footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    
    /* --- FIX LỖI KHÔNG THẤY CHỮ (QUAN TRỌNG) --- */
    /* Ép tất cả ô nhập liệu (Input, Select, Number, Date) phải có nền tối và chữ trắng */
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="base-input"] {
        background-color: #3a3b3c !important;
        border-radius: 12px !important;
        border: 1px solid #393a3b !important;
        color: white !important;
    }
    
    /* Chỉnh màu chữ bên trong ô input */
    input, .stSelectbox div, .stDateInput input, .stTimeInput input {
        color: white !important;
        background-color: transparent !important;
    }
    
    /* Chỉnh màu chữ Placeholder (chữ mờ) */
    ::placeholder { color: #b0b3b8 !important; opacity: 1; }
    
    /* Label (Nhãn phía trên ô input) */
    .stMarkdown label, .stTextInput label, .stNumberInput label, .stSelectbox label {
        color: #b0b3b8 !important;
    }

    /* --- GIAO DIỆN CARD & BUTTON --- */
    .css-card {
        background-color: #242526;
        padding: 25px;
        border-radius: 16px;
        border: 1px solid #393a3b;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    
    /* Nút bấm chính (Primary) */
    .stButton > button {
        background-color: #0084ff !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 12px 20px !important;
        height: auto !important;
        transition: 0.2s;
    }
    .stButton > button:hover { background-color: #0073e6 !important; transform: scale(0.99); }
    
    /* --- CHAT UI --- */
    .chat-container { display: flex; flex-direction: column; gap: 10px; padding: 10px; height: 60vh; overflow-y: auto; }
    .msg-row { display: flex; width: 100%; align-items: flex-end; }
    .me { justify-content: flex-end; } 
    .you { justify-content: flex-start; }
    
    .avatar {
        width: 32px; height: 32px; border-radius: 50%; margin-right: 8px; 
        background: linear-gradient(45deg, #0084ff, #00c6ff); 
        display: flex; align-items: center; justify-content: center; 
        font-size: 12px; color: white; font-weight: bold; flex-shrink: 0;
    }
    
    .bubble {
        padding: 10px 16px; border-radius: 18px; font-size: 15px; line-height: 1.4;
        max-width: 80%; word-wrap: break-word; box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    .b-me { background: #0084ff; color: white; border-bottom-right-radius: 4px; }
    .b-you { background: #3e4042; color: #e4e6eb; border-bottom-left-radius: 4px; }
    
    /* Payment Card */
    .pay-card {
        background: rgba(36, 37, 38, 0.95); border: 1px solid #42b72a;
        padding: 15px; border-radius: 18px; min-width: 220px;
    }
    
    /* --- LOGIN TABS --- */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; color: #b0b3b8; border: none; }
    .stTabs [aria-selected="true"] { color: #0084ff; font-weight: bold; border-bottom: 2px solid #0084ff; }

</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_FILE = "system_v63.db"

def get_db(): return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, branch TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS keys (key_code TEXT PRIMARY KEY, duration TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS salary (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, date TEXT, time_in TEXT, time_out TEXT, rate INTEGER, total INTEGER, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS msgs (id INTEGER PRIMARY KEY AUTOINCREMENT, branch TEXT, sender TEXT, content TEXT, type TEXT, timestamp TEXT)')
    # Super Admin mặc định
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin_vip', 'vip888', 'super_admin', 'BOSS', 'SYSTEM')")
    conn.commit(); conn.close()

init_db()

# --- 3. SESSION & UTILS ---
if 'user' not in st.session_state: st.session_state.user = None

# --- 4. GIAO DIỆN ---

# === MÀN HÌNH ĐĂNG NHẬP ===
if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 4, 1]) # Căn giữa chuẩn hơn trên mobile
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="css-card" style="text-align:center">
            <h1 style="color:#0084ff; margin:0; font-size: 28px;">SYSTEM V63</h1>
            <p style="color:#b0b3b8; font-size:14px">Phiên bản sửa lỗi hiển thị & Đăng nhập</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs Đăng nhập / Đăng ký
        tab_login, tab_reg = st.tabs(["🔑 ĐĂNG NHẬP", "📝 ĐĂNG KÝ"])
        
        with tab_login:
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            u = st.text_input("Tên đăng nhập", key="l_u")
            p = st.text_input("Mật khẩu", type="password", key="l_p")
            
            if st.button("VÀO HỆ THỐNG", use_container_width=True):
                conn = get_db(); row = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p)).fetchone(); conn.close()
                if row:
                    st.session_state.user = row[0]; st.session_state.role = row[2]; st.session_state.name = row[3]; st.session_state.branch = row[4]
                    st.rerun()
                else: st.error("Sai tài khoản hoặc mật khẩu!")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # --- PHẦN SUPER ADMIN BỊ MẤT ĐÃ ĐƯỢC ĐƯA RA ĐÂY ---
            with st.expander("🛡️ Dành cho Quản Trị Viên (Web Owner)"):
                st.info("Đăng nhập bằng tài khoản cấp cao (Super Admin) để tạo Key bán.")
                # Dùng chung form đăng nhập ở trên, chỉ cần nhập đúng admin_vip/vip888 là tự vào.

        with tab_reg:
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            ru = st.text_input("ID (Viết liền, không dấu)", key="r_u")
            rn = st.text_input("Tên hiển thị (Zalo)", key="r_n")
            rp = st.text_input("Mật khẩu mới", type="password", key="r_p")
            rr = st.selectbox("Bạn là ai?", ["Nhân viên", "Quản lý (Mua Key)"], key="r_r")
            
            role_code = 'staff' if rr == "Nhân viên" else 'admin'
            label_key = "Mã Chi Nhánh (VD: CN01)" if role_code == 'staff' else "Nhập Key Kích Hoạt"
            rk = st.text_input(label_key, key="r_k")
            
            if st.button("TẠO TÀI KHOẢN MỚI", use_container_width=True):
                if not ru or not rp or not rk:
                    st.warning("Vui lòng nhập đủ thông tin!")
                else:
                    conn = get_db()
                    try:
                        if role_code == 'admin':
                            # Check Key
                            k = conn.execute("SELECT * FROM keys WHERE key_code=? AND status='active'", (rk,)).fetchone()
                            if k:
                                conn.execute("UPDATE keys SET status='used' WHERE key_code=?", (rk,))
                                conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, role_code, rn, 'PENDING'))
                                conn.commit(); st.success("Tạo quản lý thành công! Hãy đăng nhập."); st.balloons()
                            else: st.error("Key không đúng hoặc đã được sử dụng!")
                        else:
                            # Staff
                            conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, role_code, rn, rk))
                            conn.commit(); st.success("Tạo nhân viên thành công!"); st.balloons()
                    except sqlite3.IntegrityError:
                        st.error("ID này đã có người dùng!")
                    finally:
                        conn.close()
            st.markdown('</div>', unsafe_allow_html=True)

# === MÀN HÌNH CHÍNH (SAU KHI LOGIN) ===
else:
    me = st.session_state.user; name = st.session_state.name; role = st.session_state.role; branch = st.session_state.branch
    
    # THANH MENU TRÊN CÙNG
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f"### 👋 Hi, {name}!")
        st.caption(f"Vai trò: {role} | CN: {branch}")
    with c2:
        if st.button("Đăng xuất", type="secondary"): 
            st.session_state.user = None; st.rerun()

    # --- 1. GIAO DIỆN SUPER ADMIN ---
    if role == 'super_admin':
        st.markdown('<div class="css-card"><h3 style="color:#0084ff">💎 QUẢN LÝ KEY (SUPER ADMIN)</h3>', unsafe_allow_html=True)
        st.write("Tại đây bạn tạo ra các mã Key để bán cho các chủ quán (Admin).")
        
        c_k1, c_k2 = st.columns([3, 1])
        with c_k1: dur = st.selectbox("Thời hạn gói", ["30 Ngày", "1 Năm", "Vĩnh viễn"])
        with c_k2: 
            if st.button("SINH KEY"):
                k = str(uuid.uuid4())[:8].upper()
                conn = get_db(); conn.execute("INSERT INTO keys VALUES (?,?,'active')", (k, dur)); conn.commit(); conn.close()
                st.success(f"KEY MỚI: {k}")
        
        st.write("Danh sách Key đã tạo:")
        conn = get_db(); df_k = pd.read_sql("SELECT * FROM keys", conn); conn.close()
        st.dataframe(df_k, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 2. GIAO DIỆN ADMIN CHƯA CÓ CHI NHÁNH ---
    elif role == 'admin' and branch == 'PENDING':
        st.markdown('<div class="css-card"><h3 style="color:#0084ff">🏢 KHỞI TẠO CHI NHÁNH</h3>', unsafe_allow_html=True)
        st.info("Tài khoản của bạn đã kích hoạt. Vui lòng tạo mã chi nhánh để nhân viên tham gia.")
        nb = st.text_input("Mã Chi Nhánh (VD: CN01, CAFE_A)")
        if st.button("XÁC NHẬN TẠO"):
            if nb:
                conn = get_db(); conn.execute("UPDATE users SET branch=? WHERE username=?", (nb, me)); conn.commit(); conn.close()
                st.session_state.branch = nb; st.rerun()
            else: st.warning("Nhập mã đi bạn ơi!")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. GIAO DIỆN CHÍNH (CHAT & LƯƠNG) ---
    else:
        tab_chat, tab_work = st.tabs(["💬 TIN NHẮN", "📊 CÔNG VIỆC"])
        
        # TAB CHAT
        with tab_chat:
            conn = get_db(); msgs = conn.execute("SELECT * FROM msgs WHERE branch=? ORDER BY id DESC LIMIT 50", (branch,)).fetchall()[::-1]; conn.close()
            
            # Render chat
            chat_html = '<div class="chat-container">'
            for m in msgs:
                is_me = (m[2] == me); cls = "me" if is_me else "you"; bub = "b-me" if is_me else "b-you"
                ava = "" if is_me else f'<div class="avatar">{m[2][0].upper()}</div>'
                content = f'<div class="bubble {bub}">{m[3]}</div>'
                if m[4] == 'pay':
                    content = f'<div class="pay-card"><div style="color:#42b72a;font-weight:bold;font-size:12px">💸 YÊU CẦU THANH TOÁN</div><div style="color:#b0b3b8;font-size:13px">Quản lý {m[2]} chuyển:</div><div style="font-size:20px;font-weight:bold;color:white">{int(m[3]):,} đ</div></div>'
                chat_html += f'<div class="msg-row {cls}">{ava}{content}</div>'
            chat_html += '</div>'
            
            with st.container(height=400): st.markdown(chat_html, unsafe_allow_html=True)
            
            # Input
            c_in1, c_in2 = st.columns([5, 1])
            with c_in1: txt = st.chat_input("Nhập tin nhắn...")
            with c_in2: 
                if role == 'admin':
                    if st.button("💸"): 
                        conn = get_db(); conn.execute("INSERT INTO msgs (branch, sender, content, type, timestamp) VALUES (?,?,?,?,?)", (branch, me, "0", 'pay_req', datetime.now().strftime('%H:%M'))); conn.commit(); conn.close()
                        st.info("Đã gửi yêu cầu thanh toán mẫu (Tính năng demo)")
            
            if txt:
                conn = get_db(); conn.execute("INSERT INTO msgs (branch, sender, content, type, timestamp) VALUES (?,?,?,?,?)", (branch, me, txt, 'text', datetime.now().strftime('%H:%M'))); conn.commit(); conn.close()
                st.rerun()

        # TAB CÔNG VIỆC
        with tab_work:
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            st.subheader("📝 TÍNH LƯƠNG & CHẤM CÔNG")
            
            c1, c2 = st.columns(2)
            d = c1.date_input("Ngày làm")
            
            c3, c4, c5 = st.columns(3)
            t1 = c3.time_input("Giờ vào")
            t2 = c4.time_input("Giờ ra")
            rate = c5.number_input("Lương/1h", value=20000, step=1000)
            
            # Tính toán Realtime Python
            dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
            if dt2 < dt1: dt2 += timedelta(days=1)
            hours = (dt2 - dt1).seconds / 3600
            total = int(hours * rate)
            
            st.markdown(f"<h3 style='text-align:right; color:#42b72a; margin:0'>⏳ {hours:.1f}h x {rate:,} = {total:,} VNĐ</h3>", unsafe_allow_html=True)
            
            # Chọn nhân viên (Nếu là admin)
            target_u = me
            if role == 'admin':
                conn = get_db(); staffs = [r[0] for r in conn.execute("SELECT username FROM users WHERE branch=? AND role='staff'", (branch,)).fetchall()]; conn.close()
                target_u = st.selectbox("Chấm công cho:", staffs) if staffs else None
            
            if st.button("LƯU CA LÀM VIỆC", use_container_width=True):
                if target_u:
                    conn = get_db()
                    conn.execute("INSERT INTO salary (username, date, time_in, time_out, rate, total, status) VALUES (?,?,?,?,?,?,?)",
                                (target_u, str(d), str(t1), str(t2), rate, total, 'Chờ duyệt'))
                    conn.commit(); conn.close()
                    st.success("Đã lưu!"); time.sleep(1); st.rerun()
                else: st.error("Chưa có nhân viên nào!")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Lịch sử
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            st.subheader("📜 LỊCH SỬ")
            conn = get_db()
            query = f"SELECT * FROM salary WHERE username IN (SELECT username FROM users WHERE branch='{branch}') ORDER BY id DESC" if role == 'admin' else f"SELECT * FROM salary WHERE username='{me}' ORDER BY id DESC"
            df = pd.read_sql(query, conn); conn.close()
            
            if not df.empty:
                st.dataframe(df[['date', 'username', 'total', 'status']], use_container_width=True)
                debt = df[df['status'] != 'Đã nhận']['total'].sum()
                st.metric("TỔNG NỢ LƯƠNG", f"{debt:,} VNĐ")
                
                if role == 'admin' and st.button("✅ DUYỆT TẤT CẢ", use_container_width=True):
                    conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã duyệt' WHERE username IN (SELECT username FROM users WHERE branch='{branch}')"); conn.commit(); conn.close()
                    st.rerun()
                if role == 'staff' and st.button("💰 XÁC NHẬN ĐÃ NHẬN TIỀN", use_container_width=True):
                    conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã nhận' WHERE username='{me}'"); conn.commit(); conn.close()
                    st.rerun()
            else: st.info("Chưa có dữ liệu chấm công.")
            st.markdown('</div>', unsafe_allow_html=True)