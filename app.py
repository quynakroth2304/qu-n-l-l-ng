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

# --- 1. CẤU HÌNH EMAIL (SỬA Ở ĐÂY) ---
# Cách lấy Mật khẩu ứng dụng: Vào https://myaccount.google.com/apppasswords
EMAIL_USER = "quynakroth2304@gmail.com" 
EMAIL_PASS = "njew djlz pwyv etzb"     # Mật khẩu ứng dụng 16 số (Không phải pass đăng nhập)
EMAIL_TO = "quynakroth2304@gmail.com"   # Gửi về chính email của bạn

# --- 2. CẤU HÌNH TRANG ---
st.set_page_config(page_title="System V69 Backup", layout="wide", page_icon="📧", initial_sidebar_state="collapsed")

# CSS Dark Mode
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #18191a; color: #e4e6eb; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    [data-testid="stSidebar"] { background-color: #242526; }
    
    .css-card {
        background-color: #242526; padding: 25px; border-radius: 12px;
        border: 1px solid #3a3b3c; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input {
        background-color: #3a3b3c !important; color: white !important; border: 1px solid #555 !important;
    }
    .stButton button {
        background-color: #0084ff !important; color: white !important; font-weight: bold; border: none;
    }
    .stButton button:hover { background-color: #0073e6 !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. DATABASE ---
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

# --- 4. HÀM GỬI EMAIL BACKUP (TỰ ĐỘNG) ---
def send_backup(reason):
    if "email_cua_ban" in EMAIL_USER: return # Chưa cấu hình email thì bỏ qua
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_TO
        msg['Subject'] = f"BACKUP V69: {reason} - {datetime.now().strftime('%H:%M %d/%m')}"
        
        body = "Hệ thống tự động backup dữ liệu mới nhất."
        msg.attach(MIMEText(body, 'plain'))
        
        attachment = open(DB_FILE, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {DB_FILE}")
        msg.attach(part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, EMAIL_TO, text)
        server.quit()
        # st.toast("📧 Đã gửi backup về Email!")
    except Exception as e:
        print(f"Lỗi gửi mail: {e}")

# --- 5. SESSION & KHÔI PHỤC DỮ LIỆU ---
if 'user' not in st.session_state: st.session_state.user = None

# --- 6. APP LOGIC ---
if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        st.markdown('<div class="css-card"><h1 style="text-align:center; color:#0084ff">HỆ THỐNG V69</h1><p style="text-align:center;color:#888">Bản đầy đủ: Lọc ngày + Auto Backup</p></div>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["🔑 ĐĂNG NHẬP", "📝 ĐĂNG KÝ", "♻️ KHÔI PHỤC"])
        
        with tab1:
            with st.form("login"):
                u = st.text_input("Tên đăng nhập")
                p = st.text_input("Mật khẩu", type="password")
                if st.form_submit_button("VÀO HỆ THỐNG", use_container_width=True):
                    conn = get_db(); row = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p)).fetchone(); conn.close()
                    if row:
                        st.session_state.user = row[0]; st.session_state.role = row[2]; st.session_state.name = row[3]; st.session_state.branch = row[4]
                        st.rerun()
                    else: st.error("Sai thông tin!")
        
        with tab2:
            with st.form("reg"):
                ru = st.text_input("Tên đăng nhập")
                rn = st.text_input("Tên hiển thị")
                rp = st.text_input("Mật khẩu mới", type="password")
                rr = st.selectbox("Vai trò", ["Nhân viên", "Quản lý"])
                lbl = "Mã Chi Nhánh" if rr == 'Nhân viên' else "Key Kích Hoạt"
                rk = st.text_input(lbl)
                if st.form_submit_button("ĐĂNG KÝ", use_container_width=True):
                    if not ru or not rp or not rk: st.error("Thiếu thông tin!")
                    else:
                        role_code = 'admin' if rr == 'Quản lý' else 'staff'
                        conn = get_db()
                        try:
                            if role_code == 'admin':
                                k = conn.execute("SELECT * FROM keys WHERE key_code=? AND status='active'", (rk,)).fetchone()
                                if k:
                                    conn.execute("UPDATE keys SET status='used' WHERE key_code=?", (rk,))
                                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, role_code, rn, 'PENDING'))
                                    st.success("Tạo Quản lý xong!"); send_backup(f"New Admin {ru}")
                                else: st.error("Key sai!")
                            else:
                                if conn.execute("SELECT * FROM users WHERE branch=? AND role='admin'", (rk,)).fetchone():
                                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, role_code, rn, rk))
                                    st.success("Tạo Nhân viên xong!"); send_backup(f"New Staff {ru}")
                                else: st.error("Chi nhánh không tồn tại!")
                            conn.commit()
                        except: st.error("Tên đăng nhập trùng!")
                        finally: conn.close()
        
        with tab3:
            st.info("Nếu web bị reset mất dữ liệu, hãy tải file .db từ Email về và upload vào đây.")
            uploaded_db = st.file_uploader("Chọn file system_v69.db", type="db")
            if uploaded_db:
                with open(DB_FILE, "wb") as f: f.write(uploaded_db.getbuffer())
                st.success("Đã khôi phục! Hãy đăng nhập lại."); time.sleep(2); st.rerun()

else:
    me = st.session_state.user; role = st.session_state.role; branch = st.session_state.branch
    
    # Header
    c1, c2 = st.columns([3, 1])
    with c1: st.title(f"👋 {st.session_state.name}")
    with c2: 
        if st.button("Đăng xuất"): st.session_state.user = None; st.rerun()
    st.info(f"Vai trò: **{'Quản lý' if role=='admin' else 'Nhân viên'}** | Chi nhánh: **{branch}**")

    # SUPER ADMIN
    if role == 'super_admin':
        st.markdown('<div class="css-card"><h3>💎 QUẢN LÝ KEY</h3>', unsafe_allow_html=True)
        with st.form("gk"):
            dur = st.selectbox("Hạn", ["Vĩnh viễn", "1 Tháng"])
            if st.form_submit_button("SINH KEY"):
                k = str(uuid.uuid4())[:8].upper()
                conn = get_db(); conn.execute("INSERT INTO keys VALUES (?,?,'active')", (k, dur)); conn.commit(); conn.close()
                st.success(f"Key: {k}"); send_backup("New Key Gen")
        conn = get_db(); st.dataframe(pd.read_sql("SELECT * FROM keys", conn), use_container_width=True); conn.close()
        st.markdown('</div>', unsafe_allow_html=True)

    # ADMIN TẠO CN
    elif role == 'admin' and branch == 'PENDING':
        st.markdown('<div class="css-card"><h3>🏢 TẠO CHI NHÁNH</h3>', unsafe_allow_html=True)
        nb = st.text_input("Mã Chi Nhánh Mới")
        if st.button("TẠO NGAY"):
            conn = get_db()
            if conn.execute("SELECT * FROM users WHERE branch=? AND role='admin'", (nb,)).fetchone(): st.error("Mã trùng!")
            else:
                conn.execute("UPDATE users SET branch=? WHERE username=?", (nb, me)); conn.commit(); conn.close()
                st.session_state.branch = nb; send_backup(f"New Branch {nb}"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # WORKSPACE
    else:
        tab_chat, tab_work = st.tabs(["💬 TIN NHẮN", "📊 LƯƠNG & CA"])
        
        # CHAT
        with tab_chat:
            conn = get_db(); msgs = conn.execute("SELECT * FROM msgs WHERE branch=? ORDER BY id DESC LIMIT 50", (branch,)).fetchall()[::-1]; conn.close()
            for m in msgs:
                with st.chat_message("user" if m[2] == me else "assistant", avatar="🧑‍💻" if m[2]==me else "👤"): st.write(f"**{m[2]}:** {m[3]}")
            if txt := st.chat_input("Nhập tin..."):
                conn = get_db(); conn.execute("INSERT INTO msgs (branch, sender, content, type, timestamp) VALUES (?,?,?,?,?)", (branch, me, txt, 'text', datetime.now().strftime('%H:%M'))); conn.commit(); conn.close(); st.rerun()

        # LƯƠNG
        with tab_work:
            st.markdown("### 📝 NHẬP CA LÀM")
            with st.container():
                st.markdown('<div class="css-card">', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                d = c1.date_input("Ngày làm")
                pos = c2.text_input("Vị trí", "Tại quán")
                c3, c4, c5 = st.columns(3)
                t1 = c3.time_input("Vào")
                t2 = c4.time_input("Ra")
                rate = c5.number_input("Lương/1h", value=20000, step=1000)
                
                dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                if dt2 < dt1: dt2 += timedelta(days=1)
                hours = (dt2 - dt1).seconds / 3600
                total = int(hours * rate)
                st.success(f"⏳ **{hours:.1f}h** x {rate:,} = **{total:,} VNĐ**")
                
                target = me
                if role == 'admin':
                    conn = get_db(); staffs = [r[0] for r in conn.execute("SELECT username FROM users WHERE branch=? AND role='staff'", (branch,)).fetchall()]; conn.close()
                    target = st.selectbox("Chấm cho:", staffs) if staffs else None
                
                if st.button("💾 LƯU CA LÀM VIỆC", type="primary"):
                    if target:
                        conn = get_db()
                        conn.execute("INSERT INTO salary (username, date, time_in, time_out, rate, total, status) VALUES (?,?,?,?,?,?,?)", (target, str(d), str(t1), str(t2), rate, total, 'Chờ duyệt'))
                        conn.commit(); conn.close(); st.toast("Đã lưu!"); send_backup(f"{me} added shift"); time.sleep(1); st.rerun()
                    else: st.error("Chưa có nhân viên!")
                st.markdown('</div>', unsafe_allow_html=True)

            # DANH SÁCH & BỘ LỌC
            st.markdown("### 📜 DANH SÁCH & DUYỆT")
            
            # Filter
            col_f1, col_f2 = st.columns([1, 2])
            with col_f1: view = st.radio("Xem:", ["Tất cả", "Theo ngày"])
            f_date = None
            if view == "Theo ngày":
                with col_f2: f_date = st.date_input("Chọn ngày:", datetime.now())

            conn = get_db()
            q = f"SELECT id, date, username, total, status FROM salary WHERE username IN (SELECT username FROM users WHERE branch='{branch}')" if role == 'admin' else f"SELECT id, date, total, status FROM salary WHERE username='{me}'"
            if f_date: q += f" AND date = '{str(f_date)}'"
            q += " ORDER BY id DESC"
            
            df = pd.read_sql(q, conn); conn.close()
            
            if not df.empty:
                df.insert(0, "Chọn", False)
                ed = st.data_editor(df, column_config={"Chọn": st.column_config.CheckboxColumn(default=False), "id": None, "total": st.column_config.NumberColumn(format="%d đ")}, disabled=["id","date","username","total","status"], hide_index=True, use_container_width=True)
                ids = ed[ed.Chọn == True]['id'].tolist()
                
                if role == 'admin':
                    c_a1, c_a2 = st.columns(2)
                    if c_a1.button(f"💸 TRẢ TIỀN NGAY ({len(ids)})"):
                        if ids:
                            conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã nhận' WHERE id IN ({','.join(map(str, ids))})"); conn.commit(); conn.close()
                            send_backup("Paid"); st.success("Đã trả tiền!"); st.rerun()
                    if c_a2.button(f"✅ DUYỆT CÔNG ({len(ids)})"):
                        if ids:
                            conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã duyệt' WHERE id IN ({','.join(map(str, ids))})"); conn.commit(); conn.close()
                            send_backup("Approved"); st.success("Đã duyệt!"); st.rerun()
                
                if role == 'staff':
                    if st.button(f"💰 ĐÃ NHẬN TIỀN ({len(ids)})"):
                        if ids:
                            conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã nhận' WHERE id IN ({','.join(map(str, ids))})"); conn.commit(); conn.close()
                            send_backup("Staff Confirm"); st.success("Đã xác nhận!"); st.rerun()
                
                debt = df[df['status'] != 'Đã nhận']['total'].sum()
                st.metric("TỔNG TIỀN TREO", f"{debt:,} VNĐ")
            else: st.info("Không có dữ liệu.")