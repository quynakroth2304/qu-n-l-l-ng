import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import time
from datetime import datetime

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="System V65 Security", layout="wide", page_icon="🔒", initial_sidebar_state="collapsed")

# CSS Dark Mode & Form Styles
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
    
    .error-box { color: #ff4d4d; font-weight: bold; padding: 10px; border: 1px solid #ff4d4d; border-radius: 8px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_FILE = "system_v65.db"

def get_db(): return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, branch TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS keys (key_code TEXT PRIMARY KEY, duration TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS salary (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, date TEXT, time_in TEXT, time_out TEXT, rate INTEGER, total INTEGER, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS msgs (id INTEGER PRIMARY KEY AUTOINCREMENT, branch TEXT, sender TEXT, content TEXT, type TEXT, timestamp TEXT)')
    # Tạo Super Admin
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '123', 'super_admin', 'BOSS', 'SYSTEM')")
    conn.commit(); conn.close()

init_db()

# --- 3. SESSION ---
if 'user' not in st.session_state: st.session_state.user = None

# --- 4. GIAO DIỆN LOGIN / REGISTER ---
if not st.session_state.user:
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        st.markdown('<div class="css-card"><h1 style="text-align:center; color:#0084ff">SYSTEM V65</h1><p style="text-align:center;color:#888">Bản vá lỗi bảo mật Chi Nhánh</p></div>', unsafe_allow_html=True)
        
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
                ru = st.text_input("ID (Viết liền, không dấu)")
                rn = st.text_input("Tên hiển thị")
                rp = st.text_input("Mật khẩu mới", type="password")
                rr = st.selectbox("Vai trò", ["staff", "admin"])
                # Label động
                lbl = "Mã Chi Nhánh (Nhập chính xác mã do Quản lý cấp)" if rr == 'staff' else "Key Kích Hoạt (Mua từ Super Admin)"
                rk = st.text_input(lbl)
                
                btn_reg = st.form_submit_button("TẠO TÀI KHOẢN", use_container_width=True)
                
                if btn_reg:
                    if not ru or not rp or not rk:
                        st.error("Vui lòng nhập đủ thông tin!")
                    else:
                        conn = get_db()
                        try:
                            # LOGIC ĐĂNG KÝ QUẢN LÝ
                            if rr == 'admin':
                                k = conn.execute("SELECT * FROM keys WHERE key_code=? AND status='active'", (rk,)).fetchone()
                                if k:
                                    conn.execute("UPDATE keys SET status='used' WHERE key_code=?", (rk,))
                                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, rr, rn, 'PENDING'))
                                    st.success("Tạo Quản lý thành công! Hãy đăng nhập để tạo Chi Nhánh."); st.balloons()
                                else: st.error("Key không đúng hoặc đã được sử dụng!")
                            
                            # LOGIC ĐĂNG KÝ NHÂN VIÊN (ĐÃ SỬA LỖI)
                            else:
                                # Kiểm tra xem Mã Chi Nhánh (rk) có tồn tại không (Phải có một Admin đang giữ mã này)
                                check_branch = conn.execute("SELECT * FROM users WHERE branch=? AND role='admin'", (rk,)).fetchone()
                                
                                if check_branch:
                                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ru, rp, rr, rn, rk))
                                    st.success(f"Đã tham gia vào chi nhánh {rk} thành công!"); st.balloons()
                                else:
                                    st.markdown(f'<div class="error-box">⛔ LỖI: Chi nhánh "{rk}" chưa tồn tại!<br>Vui lòng bảo Quản lý tạo chi nhánh trước.</div>', unsafe_allow_html=True)
                            
                            conn.commit()
                        except sqlite3.IntegrityError:
                            st.error("ID đăng nhập này đã có người dùng! Hãy chọn tên khác.")
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
        st.markdown('<div class="css-card"><h3>💎 QUẢN LÝ KEY (SUPER ADMIN)</h3>', unsafe_allow_html=True)
        with st.form("gen_key"):
            dur = st.selectbox("Thời hạn", ["1 Tháng", "1 Năm", "Vĩnh viễn"])
            if st.form_submit_button("SINH KEY MỚI"):
                k = str(uuid.uuid4())[:8].upper()
                conn = get_db(); conn.execute("INSERT INTO keys VALUES (?,?,'active')", (k, dur)); conn.commit(); conn.close()
                st.success(f"KEY MỚI: {k}")
        
        conn = get_db(); df = pd.read_sql("SELECT * FROM keys", conn); conn.close()
        st.dataframe(df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ADMIN KHỞI TẠO CN (ĐÃ SỬA LỖI TRÙNG MÃ) ---
    elif role == 'admin' and branch == 'PENDING':
        st.markdown('<div class="css-card"><h3>🏢 KHỞI TẠO CHI NHÁNH</h3>', unsafe_allow_html=True)
        st.warning("Bạn cần tạo mã chi nhánh để nhân viên có thể tham gia.")
        with st.form("create_branch"):
            nb = st.text_input("Mã Chi Nhánh Mới (VD: CN01)")
            if st.form_submit_button("TẠO NGAY"):
                conn = get_db()
                # Kiểm tra xem mã này đã có ai dùng chưa
                exist = conn.execute("SELECT * FROM users WHERE branch=? AND role='admin'", (nb,)).fetchone()
                if exist:
                    st.error(f"Mã '{nb}' đã có người khác sử dụng! Vui lòng chọn mã khác.")
                else:
                    conn.execute("UPDATE users SET branch=? WHERE username=?", (nb, me))
                    conn.commit()
                    st.session_state.branch = nb
                    st.success("Tạo thành công!"); time.sleep(1); st.rerun()
                conn.close()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- WORKSPACE (CHAT & LƯƠNG) ---
    else:
        tab_chat, tab_work = st.tabs(["💬 TIN NHẮN", "📊 CÔNG VIỆC"])
        
        # CHAT
        with tab_chat:
            conn = get_db(); msgs = conn.execute("SELECT * FROM msgs WHERE branch=? ORDER BY id DESC LIMIT 50", (branch,)).fetchall()[::-1]; conn.close()
            for m in msgs:
                with st.chat_message("user" if m[2] == me else "assistant", avatar="🧑‍💻" if m[2]==me else "👤"):
                    st.write(f"**{m[2]}:** {m[3]}")
            
            if txt := st.chat_input("Nhập tin nhắn..."):
                conn = get_db(); conn.execute("INSERT INTO msgs (branch, sender, content, type, timestamp) VALUES (?,?,?,?,?)", 
                                            (branch, me, txt, 'text', datetime.now().strftime('%H:%M'))); conn.commit(); conn.close()
                st.rerun()

        # LƯƠNG
        with tab_work:
            st.markdown("### 📝 TÍNH LƯƠNG & CA")
            with st.container():
                st.markdown('<div class="css-card">', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                d = col1.date_input("Ngày làm")
                
                # Sửa lỗi: Nhân viên tự nhập vị trí, Admin thì ko cần
                pos = col2.text_input("Vị trí", "Tại quán")
                
                c3, c4, c5 = st.columns(3)
                t1 = c3.time_input("Giờ vào")
                t2 = c4.time_input("Giờ ra")
                rate = c5.number_input("Lương/1h", value=20000, step=1000)
                
                dt1 = datetime.combine(d, t1); dt2 = datetime.combine(d, t2)
                if dt2 < dt1: dt2 += timedelta(days=1)
                hours = (dt2 - dt1).seconds / 3600
                total = int(hours * rate)
                
                st.success(f"⏳ Thời gian: **{hours:.1f} giờ** | 💰 Thành tiền: **{total:,} VNĐ**")
                
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
                    else: st.error("Chưa có nhân viên nào trong chi nhánh này!")
                st.markdown('</div>', unsafe_allow_html=True)

            # Lịch sử
            st.markdown("### 📜 LỊCH SỬ")
            conn = get_db()
            df = pd.read_sql(f"SELECT * FROM salary WHERE username IN (SELECT username FROM users WHERE branch='{branch}') ORDER BY id DESC" if role == 'admin' else f"SELECT * FROM salary WHERE username='{me}' ORDER BY id DESC", conn)
            conn.close()
            
            if not df.empty:
                st.dataframe(df[['date', 'username', 'time_in', 'time_out', 'total', 'status']], use_container_width=True)
                debt = df[df['status'] != 'Đã nhận']['total'].sum()
                st.metric("TỔNG NỢ LƯƠNG", f"{debt:,} VNĐ")
                
                c_btn1, c_btn2 = st.columns(2)
                if role == 'admin' and c_btn1.button("✅ DUYỆT TẤT CẢ"):
                    conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã duyệt' WHERE username IN (SELECT username FROM users WHERE branch='{branch}')"); conn.commit(); conn.close()
                    st.rerun()
                if role == 'staff' and c_btn2.button("💰 ĐÃ NHẬN TIỀN"):
                    conn = get_db(); conn.execute(f"UPDATE salary SET status='Đã nhận' WHERE username='{me}'"); conn.commit(); conn.close()
                    st.rerun()
            else: st.info("Chưa có dữ liệu.")