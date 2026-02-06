import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime, timedelta

# --- 1. CẤU HÌNH ---
# Điền email nếu muốn gửi báo cáo
EMAIL_USER = "quynakroth2304@gmail.com" 
EMAIL_PASS = "njew djlz pwyv etzb"     
EMAIL_TO = "quynakroth2304@gmail.com"   

st.set_page_config(page_title="Hệ Thống Lương V83", layout="wide", page_icon="⏰", initial_sidebar_state="collapsed")

# CSS Dark Mode
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #18191a; color: #e4e6eb; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    .css-card { background-color: #242526; padding: 25px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #3a3b3c; }
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input { background-color: #3a3b3c !important; color: white !important; }
    .stButton button { background-color: #0084ff !important; color: white !important; font-weight: bold; border: none; }
    
    /* Highlight cột giờ vào ra */
    [data-testid="stDataFrame"] { font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE (DÙNG FILE system_v69.db CỦA BẠN) ---
DB_FILE = "system_v69.db"

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

# --- 3. LOGIC APP ---
if 'user' not in st.session_state: st.session_state.user = None

# MÀN HÌNH ĐĂNG NHẬP
if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        st.markdown('<div class="css-card"><h1 style="text-align:center; color:#0084ff">CHẤM CÔNG V83</h1><p style="text-align:center">Đã sửa lỗi hiển thị giờ</p></div>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["🔑 ĐĂNG NHẬP", "📝 ĐĂNG KÝ", "♻️ KHÔI PHỤC"])
        
        with tab1:
            with st.form("login"):
                u = st.text_input("Tên đăng nhập")
                p = st.text_input("Mật khẩu", type="password")
                if st.form_submit_button("VÀO HỆ THỐNG", use_container_width=True):
                    conn = get_db()
                    row = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p)).fetchone()
                    conn.close()
                    if row:
                        st.session_state.user = row[0]; st.session_state.role = row[2]
                        st.session_state.name = row[3]; st.session_state.branch = row[4]
                        st.rerun()
                    else: st.error("Sai tài khoản hoặc mật khẩu!")
        
        with tab2:
            with st.form("reg"):
                ru = st.text_input("Tên đăng nhập"); rn = st.text_input("Tên hiển thị"); rp = st.text_input("Mật khẩu", type="password")
                rr = st.selectbox("Vai trò", ["Nhân viên", "Quản lý"])
                lbl = "Mã Chi Nhánh" if rr == 'Nhân viên' else "Key Kích Hoạt"
                rk = st.text_input(lbl)
                if st.form_submit_button("ĐĂNG KÝ"):
                    role_code = 'admin' if rr == 'Quản lý' else 'staff'
                    conn = get_db()
                    try:
                        if role_code == 'admin':
                            k = conn.execute("SELECT * FROM keys WHERE key_code=? AND status='active'", (rk,)).fetchone()
                            if k:
                                conn.execute("UPDATE keys SET status='used' WHERE key_code=?", (rk,))
                                conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, role_code, rn, 'PENDING'))
                                st.success("Thành công!"); st.balloons()
                            else: st.error("Key sai!")
                        else:
                            if conn.execute("SELECT * FROM users WHERE branch=? AND role='admin'", (rk,)).fetchone():
                                conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, role_code, rn, rk))
                                st.success("Thành công!"); st.balloons()
                            else: st.error("Chi nhánh không tồn tại!")
                        conn.commit()
                    except: st.error("Trùng tên đăng nhập!")
                    finally: conn.close()
        
        with tab3:
            st.info("Upload file system_v69.db để khôi phục.")
            uploaded_db = st.file_uploader("Chọn file .db", type="db")
            if uploaded_db:
                with open(DB_FILE, "wb") as f: f.write(uploaded_db.getbuffer())
                st.success("Đã khôi phục! Đăng nhập lại nhé."); time.sleep(2)

# MÀN HÌNH CHÍNH
else:
    me = st.session_state.user; role = st.session_state.role; branch = st.session_state.branch
    
    c1, c2 = st.columns([3, 1])
    with c1: st.title(f"👋 {st.session_state.name} ({role})")
    with c2: 
        if st.button("Đăng xuất"): st.session_state.user = None; st.rerun()

    if role == 'super_admin':
        st.markdown("### SUPER ADMIN PANEL")
        with st.form("gk"):
            if st.form_submit_button("SINH KEY"):
                k = str(uuid.uuid4())[:8].upper()
                conn = get_db(); conn.execute("INSERT INTO keys VALUES (?,?,'active')", (k, "Vĩnh viễn")); conn.commit(); conn.close()
                st.success(f"Key: {k}")
        conn = get_db(); st.dataframe(pd.read_sql("SELECT * FROM keys", conn), use_container_width=True); conn.close()

    elif role == 'admin' and branch == 'PENDING':
        nb = st.text_input("Tạo Mã Chi Nhánh Mới")
        if st.button("Tạo"):
            conn = get_db(); conn.execute("UPDATE users SET branch=? WHERE username=?", (nb, me)); conn.commit(); conn.close()
            st.session_state.branch = nb; st.rerun()

    else:
        tab_chat, tab_work = st.tabs(["💬 CHAT", "📊 LƯƠNG & GIỜ LÀM"])
        
        with tab_chat:
            conn = get_db(); msgs = conn.execute("SELECT * FROM msgs WHERE branch=? ORDER BY id DESC LIMIT 50", (branch,)).fetchall()[::-1]; conn.close()
            for m in msgs:
                with st.chat_message("user" if m[2] == me else "assistant"): st.write(f"**{m[2]}:** {m[3]}")
            if txt := st.chat_input("Nhập tin..."):
                conn = get_db(); conn.execute("INSERT INTO msgs (branch, sender, content, type, timestamp) VALUES (?,?,?,?,?)", (branch, me, txt, 'text', datetime.now().strftime('%H:%M'))); conn.commit(); conn.close(); st.rerun()

        with tab_work:
            # --- FORM CHẤM CÔNG ---
            st.markdown("### 📝 Chấm Công Hôm Nay")
            with st.container():
                st.markdown('<div class="css-card">', unsafe_allow_html=True)
                with st.form("cc"):
                    c1, c2 = st.columns(2)
                    d = c1.date_input("Ngày làm việc")
                    rate = c2.number_input("Lương/giờ", value=23000, step=1000)
                    
                    c3, c4 = st.columns(2)
                    t1 = c3.time_input("Giờ BẮT ĐẦU")
                    t2 = c4.time_input("Giờ KẾT THÚC")
                    
                    target = me
                    if role == 'admin':
                        conn = get_db(); staffs = [r[0] for r in conn.execute("SELECT username FROM users WHERE branch=? AND role='staff'", (branch,)).fetchall()]; conn.close()
                        target = st.selectbox("Chấm cho nhân viên:", staffs) if staffs else None

                    if st.form_submit_button("Lưu Ca Làm"):
                        if target:
                            dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                            if dt2 < dt1: dt2 += timedelta(days=1) # Qua đêm
                            
                            hours = (dt2 - dt1).seconds / 3600
                            total = int(hours * rate)
                            
                            conn = get_db()
                            conn.execute("INSERT INTO salary (username, date, time_in, time_out, rate, total, status) VALUES (?,?,?,?,?,?,?)", 
                                        (target, str(d), str(t1), str(t2), rate, total, 'Chờ duyệt'))
                            conn.commit(); conn.close()
                            st.success(f"Đã lưu: {hours:.1f} tiếng ({str(t1)} - {str(t2)})")
                            time.sleep(1); st.rerun()
                        else: st.error("Chưa có nhân viên nào!")
                st.markdown('</div>', unsafe_allow_html=True)

            # --- BẢNG LƯƠNG HIỂN THỊ GIỜ RA/VÀO ---
            st.markdown("### 📜 Lịch Sử Làm Việc")
            conn = get_db()
            q = f"SELECT * FROM salary WHERE username IN (SELECT username FROM users WHERE branch='{branch}')" if role == 'admin' else f"SELECT * FROM salary WHERE username='{me}'"
            df = pd.read_sql(q + " ORDER BY id DESC", conn); conn.close()
            
            if not df.empty:
                # 🔥 CHỌN CỘT VÀ ĐỔI TÊN CHO DỄ NHÌN 🔥
                df_show = df[['date', 'username', 'time_in', 'time_out', 'rate', 'total', 'status']].copy()
                df_show.columns = ['Ngày', 'Nhân viên', 'Giờ Vào', 'Giờ Ra', 'Lương/h', 'Thành tiền', 'Trạng thái']
                
                # Hiển thị bảng
                st.dataframe(df_show, use_container_width=True, hide_index=True)
                
                # Tính tổng
                total_pending = df[df['status'] != 'Đã nhận']['total'].sum()
                st.metric("💰 TỔNG LƯƠNG CHƯA NHẬN", f"{total_pending:,} VNĐ")
                
                if role == 'admin':
                    if st.button("✅ Duyệt tất cả lương"):
                        conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã duyệt' WHERE username IN (SELECT username FROM users WHERE branch='{branch}')"); conn.commit(); conn.close(); st.rerun()
                if role == 'staff':
                    if st.button("💸 Xác nhận đã nhận tiền"):
                        conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã nhận' WHERE username='{me}'"); conn.commit(); conn.close(); st.rerun()
            else:
                st.info("Chưa có dữ liệu chấm công.")