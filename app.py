import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
from datetime import datetime, timedelta

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="System V62", layout="wide", page_icon="💎", initial_sidebar_state="collapsed")

# --- 1. ÉP GIAO DIỆN V58 VÀO STREAMLIT (CSS) ---
# Tôi lấy y nguyên CSS từ file index.html bạn gửi để đè lên giao diện Streamlit
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    
    /* --- CORE THEME --- */
    .stApp { background-color: #18191a; font-family: 'Segoe UI', sans-serif; }
    
    /* Ẩn Header/Footer mặc định của Streamlit */
    header, footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    
    /* --- CARD STYLE (Giống V58) --- */
    div[data-testid="stVerticalBlock"] > div {
        border-radius: 16px;
    }
    
    .css-card {
        background-color: #242526;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #393a3b;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        margin-bottom: 20px;
    }
    
    /* --- INPUT FIELDS --- */
    /* Ép kiểu ô nhập liệu cho giống Messenger */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div, .stDateInput input, .stTimeInput input {
        background-color: #3a3b3c !important;
        color: #e4e6eb !important;
        border: 1px solid #393a3b !important;
        border-radius: 12px !important;
        padding: 10px 15px !important;
    }
    
    /* --- BUTTONS --- */
    .stButton > button {
        background-color: #0084ff !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 10px 20px !important;
        transition: 0.2s;
        width: 100%;
    }
    .stButton > button:hover { background-color: #0073e6 !important; transform: scale(0.98); }
    
    /* Nút phụ (Secondary) */
    div[data-testid="column"] .stButton > button:nth-child(2) {
        background-color: #3a3b3c !important;
    }

    /* --- CHAT BUBBLES (HTML RENDER) --- */
    .chat-container { display: flex; flex-direction: column; gap: 10px; padding: 10px; }
    .msg-row { display: flex; width: 100%; align-items: flex-end; }
    .me { justify-content: flex-end; } 
    .you { justify-content: flex-start; }
    
    .avatar {
        width: 32px; height: 32px; border-radius: 50%; margin-right: 8px; 
        background: #555; display: flex; align-items: center; justify-content: center; 
        font-size: 12px; color: white; flex-shrink: 0;
    }
    
    .bubble {
        padding: 10px 16px; border-radius: 18px; font-size: 15px; line-height: 1.4;
        max-width: 75%; word-wrap: break-word; box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .b-me { background: #0084ff; color: white; border-bottom-right-radius: 4px; }
    .b-you { background: #3e4042; color: #e4e6eb; border-bottom-left-radius: 4px; }
    
    /* Payment Card */
    .pay-card {
        background: rgba(36, 37, 38, 0.95); border: 1px solid #42b72a;
        padding: 15px; border-radius: 18px; min-width: 220px;
    }
    
    /* --- METRIC BOX --- */
    div[data-testid="stMetricValue"] { font-size: 26px; color: #0084ff; font-weight: 800; }
    div[data-testid="stMetricLabel"] { color: #b0b3b8; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE & LOGIC ---
DB_FILE = "system_v62.db"

def get_db(): return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, branch TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS keys (key_code TEXT PRIMARY KEY, duration TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS salary (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, date TEXT, time_in TEXT, time_out TEXT, rate INTEGER, total INTEGER, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS msgs (id INTEGER PRIMARY KEY AUTOINCREMENT, branch TEXT, sender TEXT, content TEXT, type TEXT, timestamp TEXT)')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '123', 'super_admin', 'BOSS', 'SYSTEM')")
    conn.commit(); conn.close()

init_db()

# --- 3. GIAO DIỆN CHÍNH ---
if 'user' not in st.session_state: st.session_state.user = None

# MÀN HÌNH ĐĂNG NHẬP (STYLE CARD)
if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div class="css-card" style="text-align:center">
            <h2 style="color:#0084ff; margin:0">SYSTEM V62</h2>
            <p style="color:#b0b3b8; font-size:14px">Quản Lý Nhân Sự & Tiền Lương</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab_login, tab_reg = st.tabs(["Đăng Nhập", "Đăng Ký"])
        
        with tab_login:
            with st.container():
                st.markdown('<div class="css-card">', unsafe_allow_html=True)
                u = st.text_input("Tên đăng nhập")
                p = st.text_input("Mật khẩu", type="password")
                if st.button("ĐĂNG NHẬP NGAY"):
                    conn = get_db(); row = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p)).fetchone(); conn.close()
                    if row:
                        st.session_state.user = row[0]; st.session_state.role = row[2]; st.session_state.name = row[3]; st.session_state.branch = row[4]
                        st.rerun()
                    else: st.error("Sai thông tin!")
                st.markdown('</div>', unsafe_allow_html=True)

        with tab_reg:
            with st.container():
                st.markdown('<div class="css-card">', unsafe_allow_html=True)
                ru = st.text_input("ID (Viết liền)")
                rn = st.text_input("Tên hiển thị")
                rp = st.text_input("Mật khẩu mới", type="password")
                rr = st.selectbox("Vai trò", ["staff", "admin"])
                rk = st.text_input("Key (Admin) hoặc Mã CN (Staff)")
                
                if st.button("TẠO TÀI KHOẢN"):
                    conn = get_db()
                    if rr == 'admin':
                        k = conn.execute("SELECT * FROM keys WHERE key_code=? AND status='active'", (rk,)).fetchone()
                        if k:
                            conn.execute("UPDATE keys SET status='used' WHERE key_code=?", (rk,))
                            conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, rr, rn, 'PENDING'))
                            conn.commit(); st.success("Thành công! Đăng nhập đi."); st.balloons()
                        else: st.error("Key sai!")
                    else:
                        conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, rr, rn, rk))
                        conn.commit(); st.success("Thành công!"); st.balloons()
                    conn.close()
                st.markdown('</div>', unsafe_allow_html=True)

# MÀN HÌNH CHÍNH (APP)
else:
    me = st.session_state.user; name = st.session_state.name; role = st.session_state.role; branch = st.session_state.branch
    
    # HEADER
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f"### 👋 {name} <span style='font-size:14px;color:#b0b3b8'>({role}) | {branch}</span>", unsafe_allow_html=True)
    with c2:
        if st.button("🚪 Đăng xuất"): st.session_state.user = None; st.rerun()

    # SUPER ADMIN PANEL
    if role == 'super_admin':
        st.markdown('<div class="css-card"><h3>💎 QUẢN LÝ KEY</h3>', unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1: dur = st.selectbox("Thời hạn", ["1 Tháng", "1 Năm", "Vĩnh viễn"])
        with col2: 
            if st.button("Sinh Key"):
                k = str(uuid.uuid4())[:8].upper()
                conn = get_db(); conn.execute("INSERT INTO keys VALUES (?,?,'active')", (k, dur)); conn.commit(); conn.close()
                st.success(f"KEY: {k}")
        
        conn = get_db(); df_k = pd.read_sql("SELECT * FROM keys", conn); conn.close()
        st.dataframe(df_k, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ADMIN PANEL (Tạo chi nhánh)
    elif role == 'admin' and branch == 'PENDING':
        st.markdown('<div class="css-card"><h3>🏢 KHỞI TẠO CHI NHÁNH</h3>', unsafe_allow_html=True)
        nb = st.text_input("Nhập Mã Chi Nhánh (VD: CN01)")
        if st.button("XÁC NHẬN TẠO"):
            conn = get_db(); conn.execute("UPDATE users SET branch=? WHERE username=?", (nb, me)); conn.commit(); conn.close()
            st.session_state.branch = nb; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # MAIN WORKSPACE
    else:
        tab_chat, tab_work = st.tabs(["💬 Tin Nhắn", "📊 Công Việc"])
        
        # --- TAB CHAT ---
        with tab_chat:
            # Render Chat bằng HTML để giống V58
            conn = get_db(); msgs = conn.execute("SELECT * FROM msgs WHERE branch=? ORDER BY id DESC LIMIT 50", (branch,)).fetchall()[::-1]; conn.close()
            
            chat_html = '<div class="chat-container">'
            for m in msgs:
                is_me = (m[2] == me); cls = "me" if is_me else "you"; bub = "b-me" if is_me else "b-you"
                ava = "" if is_me else f'<div class="avatar">{m[2][0].upper()}</div>'
                
                content = f'<div class="bubble {bub}">{m[3]}</div>'
                if m[4] == 'pay':
                    content = f'<div class="pay-card"><div style="color:#42b72a;font-weight:bold;font-size:12px">💸 YÊU CẦU THANH TOÁN</div><div style="color:#b0b3b8;font-size:13px">Quản lý {m[2]} chuyển:</div><div style="font-size:20px;font-weight:bold;color:white">{int(m[3]):,} đ</div></div>'
                
                chat_html += f'<div class="msg-row {cls}">{ava}{content}</div>'
            chat_html += '</div>'
            
            # Khung chat cuộn
            with st.container(height=400):
                st.markdown(chat_html, unsafe_allow_html=True)
            
            # Input bar
            c1, c2 = st.columns([5, 1])
            with c1: txt = st.chat_input("Nhập tin nhắn...")
            with c2: 
                if role == 'admin' and st.button("💸"):
                    # Logic báo chuyển khoản
                    pass 
            
            if txt:
                conn = get_db(); conn.execute("INSERT INTO msgs (branch, sender, content, type, timestamp) VALUES (?,?,?,?,?)", 
                                            (branch, me, txt, 'text', datetime.now().strftime('%H:%M'))); conn.commit(); conn.close()
                st.rerun()

        # --- TAB CÔNG VIỆC ---
        with tab_work:
            # 1. Báo Cáo / Thêm Ca (Tính lương tự động)
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            st.subheader("📝 TÍNH LƯƠNG & CA LÀM")
            
            c1, c2 = st.columns(2)
            d = c1.date_input("Ngày làm")
            pos = c2.text_input("Vị trí", "Tại quán")
            
            c3, c4, c5 = st.columns(3)
            t1 = c3.time_input("Giờ vào")
            t2 = c4.time_input("Giờ ra")
            rate = c5.number_input("Lương/1h", value=20000, step=1000)
            
            # Logic tính toán Real-time của Python
            dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
            if dt2 < dt1: dt2 += timedelta(days=1)
            hours = (dt2 - dt1).seconds / 3600
            total = int(hours * rate)
            
            st.markdown(f"<div style='text-align:right; color:#42b72a; font-weight:bold'>⏳ {hours:.1f}h x {rate:,} = {total:,} VNĐ</div>", unsafe_allow_html=True)
            
            target_u = me
            if role == 'admin':
                conn = get_db(); staffs = [r[0] for r in conn.execute("SELECT username FROM users WHERE branch=? AND role='staff'", (branch,)).fetchall()]; conn.close()
                target_u = st.selectbox("Chọn nhân viên:", staffs) if staffs else None
            
            if st.button("LƯU CA LÀM VIỆC"):
                if target_u:
                    conn = get_db()
                    conn.execute("INSERT INTO salary (username, date, time_in, time_out, rate, total, status) VALUES (?,?,?,?,?,?,?)",
                                (target_u, str(d), str(t1), str(t2), rate, total, 'Chờ duyệt'))
                    conn.commit(); conn.close()
                    st.success("Đã lưu!"); time.sleep(1); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 2. Lịch sử & Duyệt
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            st.subheader("📜 LỊCH SỬ CHI TIẾT")
            
            conn = get_db()
            if role == 'admin':
                df = pd.read_sql(f"SELECT * FROM salary WHERE username IN (SELECT username FROM users WHERE branch='{branch}') ORDER BY id DESC", conn)
            else:
                df = pd.read_sql(f"SELECT * FROM salary WHERE username='{me}' ORDER BY id DESC", conn)
            conn.close()
            
            if not df.empty:
                st.dataframe(df[['date', 'username', 'total', 'status']], use_container_width=True)
                
                debt = df[df['status'] != 'Đã nhận']['total'].sum()
                st.metric("TỔNG NỢ LƯƠNG", f"{debt:,} VNĐ")
                
                if role == 'admin' and st.button("✅ DUYỆT TẤT CẢ"):
                    conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã duyệt' WHERE username IN (SELECT username FROM users WHERE branch='{branch}')"); conn.commit(); conn.close()
                    st.rerun()
                
                if role == 'staff' and st.button("💰 XÁC NHẬN ĐÃ NHẬN TIỀN"):
                    conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã nhận' WHERE username='{me}'"); conn.commit(); conn.close()
                    st.rerun()
            else:
                st.info("Chưa có dữ liệu.")
            st.markdown('</div>', unsafe_allow_html=True)