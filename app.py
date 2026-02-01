import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
from datetime import datetime

# --- 1. CẤU HÌNH & CSS DARK MODE CHUẨN ---
st.set_page_config(page_title="System V64", layout="wide", page_icon="🛡️", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Ép Dark Mode cưỡng bức */
    [data-testid="stAppViewContainer"] { background-color: #18191a; color: #e4e6eb; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    [data-testid="stSidebar"] { background-color: #242526; }
    
    /* Card Style cho các khối */
    .css-card {
        background-color: #242526; padding: 20px; border-radius: 12px;
        border: 1px solid #3a3b3c; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    
    /* Input & Button đẹp */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input {
        background-color: #3a3b3c !important; color: white !important; border: 1px solid #555 !important;
    }
    .stButton button {
        background-color: #0084ff !important; color: white !important; font-weight: bold; border: none;
    }
    .stButton button:hover { background-color: #0073e6 !important; }
    
    /* Tiêu đề */
    h1, h2, h3 { color: #0084ff !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_FILE = "system_v64_stable.db"

def get_db(): return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, branch TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS keys (key_code TEXT PRIMARY KEY, duration TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS salary (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, date TEXT, time_in TEXT, time_out TEXT, rate INTEGER, total INTEGER, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS msgs (id INTEGER PRIMARY KEY AUTOINCREMENT, branch TEXT, sender TEXT, content TEXT, type TEXT, timestamp TEXT)')
    # Tạo Super Admin: admin / 123
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '123', 'super_admin', 'BOSS', 'SYSTEM')")
    conn.commit(); conn.close()

init_db()

# --- 3. SESSION ---
if 'user' not in st.session_state: st.session_state.user = None

# --- 4. GIAO DIỆN LOGIN (Fix lỗi mất chữ) ---
if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        st.markdown('<div class="css-card"><h1 style="text-align:center">SYSTEM V64</h1></div>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔑 ĐĂNG NHẬP", "📝 ĐĂNG KÝ"])
        
        with tab1:
            with st.form("login_form"):
                u = st.text_input("Tên đăng nhập")
                p = st.text_input("Mật khẩu", type="password")
                btn = st.form_submit_button("VÀO HỆ THỐNG", use_container_width=True)
                
                if btn:
                    conn = get_db(); row = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p)).fetchone(); conn.close()
                    if row:
                        st.session_state.user = row[0]; st.session_state.role = row[2]; st.session_state.name = row[3]; st.session_state.branch = row[4]
                        st.rerun()
                    else: st.error("Sai tài khoản hoặc mật khẩu!")

        with tab2:
            with st.form("reg_form"):
                ru = st.text_input("ID (Viết liền)")
                rn = st.text_input("Tên hiển thị")
                rp = st.text_input("Mật khẩu mới", type="password")
                rr = st.selectbox("Vai trò", ["staff", "admin"])
                rk = st.text_input("Mã CN (Nhân viên) hoặc KEY (Quản lý)")
                btn_reg = st.form_submit_button("TẠO TÀI KHOẢN", use_container_width=True)
                
                if btn_reg:
                    conn = get_db()
                    try:
                        if rr == 'admin':
                            k = conn.execute("SELECT * FROM keys WHERE key_code=? AND status='active'", (rk,)).fetchone()
                            if k:
                                conn.execute("UPDATE keys SET status='used' WHERE key_code=?", (rk,))
                                conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, rr, rn, 'PENDING'))
                                st.success("Tạo Quản lý thành công!"); st.balloons()
                            else: st.error("Key sai hoặc đã dùng!")
                        else:
                            conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, rr, rn, rk))
                            st.success("Tạo Nhân viên thành công!"); st.balloons()
                        conn.commit()
                    except: st.error("ID đã tồn tại!")
                    finally: conn.close()

# --- 5. GIAO DIỆN CHÍNH ---
else:
    me = st.session_state.user; role = st.session_state.role; branch = st.session_state.branch
    
    # Header
    c1, c2 = st.columns([3, 1])
    with c1: st.title(f"👋 {st.session_state.name}")
    with c2: 
        if st.button("Đăng xuất"): st.session_state.user = None; st.rerun()
    
    st.info(f"Vai trò: {role} | Chi nhánh: {branch}")

    # --- SUPER ADMIN ---
    if role == 'super_admin':
        st.markdown("---")
        st.header("💎 QUẢN LÝ KEY (SUPER ADMIN)")
        with st.form("gen_key"):
            dur = st.selectbox("Thời hạn", ["1 Tháng", "1 Năm", "Vĩnh viễn"])
            if st.form_submit_button("SINH KEY MỚI"):
                k = str(uuid.uuid4())[:8].upper()
                conn = get_db(); conn.execute("INSERT INTO keys VALUES (?,?,'active')", (k, dur)); conn.commit(); conn.close()
                st.success(f"KEY MỚI: {k}")
        
        conn = get_db(); df = pd.read_sql("SELECT * FROM keys", conn); conn.close()
        st.dataframe(df, use_container_width=True)

    # --- ADMIN KHỞI TẠO CN ---
    elif role == 'admin' and branch == 'PENDING':
        st.warning("Bạn chưa có chi nhánh!")
        with st.form("create_branch"):
            nb = st.text_input("Mã Chi Nhánh Mới (VD: CN01)")
            if st.form_submit_button("TẠO NGAY"):
                conn = get_db(); conn.execute("UPDATE users SET branch=? WHERE username=?", (nb, me)); conn.commit(); conn.close()
                st.session_state.branch = nb; st.rerun()

    # --- WORKSPACE ---
    else:
        tab_chat, tab_work = st.tabs(["💬 TIN NHẮN", "📊 CÔNG VIỆC"])
        
        # CHAT (Native Streamlit Chat)
        with tab_chat:
            conn = get_db(); msgs = conn.execute("SELECT * FROM msgs WHERE branch=? ORDER BY id DESC LIMIT 50", (branch,)).fetchall()[::-1]; conn.close()
            
            # Hiển thị tin nhắn cũ
            for m in msgs:
                with st.chat_message("user" if m[2] == me else "assistant", avatar="🧑‍💻" if m[2]==me else "👤"):
                    st.write(f"**{m[2]}:** {m[3]}")
            
            # Nhập tin mới
            if txt := st.chat_input("Nhập tin nhắn..."):
                conn = get_db(); conn.execute("INSERT INTO msgs (branch, sender, content, type, timestamp) VALUES (?,?,?,?,?)", 
                                            (branch, me, txt, 'text', datetime.now().strftime('%H:%M'))); conn.commit(); conn.close()
                st.rerun()

        # CÔNG VIỆC
        with tab_work:
            st.markdown("### 📝 TÍNH LƯƠNG & CA")
            
            # Form tính lương (Dùng st.form để gom nhóm)
            with st.container():
                st.markdown('<div class="css-card">', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                d = col1.date_input("Ngày làm")
                pos = col2.text_input("Vị trí", "Tại quán")
                
                c3, c4, c5 = st.columns(3)
                t1 = c3.time_input("Giờ vào")
                t2 = c4.time_input("Giờ ra")
                rate = c5.number_input("Lương/1h", value=20000, step=1000)
                
                # Logic tính toán (Python xử lý)
                dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                if dt2 < dt1: dt2 += timedelta(days=1)
                hours = (dt2 - dt1).seconds / 3600
                total = int(hours * rate)
                
                st.success(f"⏳ Thời gian: **{hours:.1f} giờ** | 💰 Thành tiền: **{total:,} VNĐ**")
                
                # Chọn người để lưu (Admin được chọn, Staff tự lưu cho mình)
                target = me
                if role == 'admin':
                    conn = get_db(); staffs = [r[0] for r in conn.execute("SELECT username FROM users WHERE branch=? AND role='staff'", (branch,)).fetchall()]; conn.close()
                    target = st.selectbox("Lưu cho nhân viên:", staffs) if staffs else None
                
                if st.button("💾 LƯU CA LÀM VIỆC", type="primary"):
                    if target:
                        conn = get_db()
                        conn.execute("INSERT INTO salary (username, date, time_in, time_out, rate, total, status) VALUES (?,?,?,?,?,?,?)",
                                    (target, str(d), str(t1), str(t2), rate, total, 'Chờ duyệt'))
                        conn.commit(); conn.close()
                        st.toast("Đã lưu thành công!"); time.sleep(1); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            # Lịch sử
            st.markdown("### 📜 LỊCH SỬ CHI TIẾT")
            conn = get_db()
            if role == 'admin':
                df = pd.read_sql(f"SELECT * FROM salary WHERE username IN (SELECT username FROM users WHERE branch='{branch}') ORDER BY id DESC", conn)
            else:
                df = pd.read_sql(f"SELECT * FROM salary WHERE username='{me}' ORDER BY id DESC", conn)
            conn.close()
            
            if not df.empty:
                st.dataframe(df[['date', 'username', 'time_in', 'time_out', 'total', 'status']], use_container_width=True)
                
                # Tổng nợ
                debt = df[df['status'] != 'Đã nhận']['total'].sum()
                st.metric("TỔNG TIỀN ĐANG NỢ", f"{debt:,} VNĐ")
                
                c_btn1, c_btn2 = st.columns(2)
                if role == 'admin' and c_btn1.button("✅ DUYỆT TẤT CẢ"):
                    conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã duyệt' WHERE username IN (SELECT username FROM users WHERE branch='{branch}')"); conn.commit(); conn.close()
                    st.rerun()
                
                if role == 'staff' and c_btn2.button("💰 ĐÃ NHẬN TIỀN"):
                    conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã nhận' WHERE username='{me}'"); conn.commit(); conn.close()
                    st.rerun()
            else:
                st.info("Chưa có dữ liệu.")