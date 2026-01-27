import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from PIL import Image

# --- CẤU HÌNH ---
DB_FILE = "system_users.db"
# Lưu ý: Trên Vercel, dữ liệu SQLite sẽ reset nếu không dùng DB ngoài. 
# Nhưng đây là cách nhanh nhất để bạn chạy thử nghiệm.
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT, qr_path TEXT)')
conn.commit()

def find_col(df, key):
    for col in df.columns:
        if key.lower() in str(col).lower(): return col
    return None

# --- GIAO DIỆN ĐĂNG NHẬP ---
if 'user' not in st.session_state:
    st.title("🛡️ Hệ Thống Quản Lý Lương Duy Trường")
    t1, t2 = st.tabs(["Đăng nhập", "Đăng ký"])
    with t1:
        u_log = st.text_input("Tên đăng nhập")
        p_log = st.text_input("Mật khẩu", type='password')
        if st.button("Vào hệ thống"):
            c.execute('SELECT * FROM users WHERE username=? AND password=?', (u_log, p_log))
            if c.fetchone():
                st.session_state.user = u_log
                st.rerun()
            else: st.error("Sai tài khoản/mật khẩu")
    with t2:
        u_reg = st.text_input("Tên đăng ký")
        p_reg = st.text_input("Mật khẩu mới", type='password')
        if st.button("Tạo tài khoản"):
            try:
                c.execute('INSERT INTO users(username, password) VALUES (?,?)', (u_reg, p_reg))
                conn.commit()
                st.success("Đăng ký thành công!")
            except: st.error("Tên này đã tồn tại.")
    st.stop()

# --- SAU KHI VÀO WEB ---
user = st.session_state.user
user_dir = f"data_{user}"
if not os.path.exists(user_dir): os.makedirs(user_dir)
excel_path = os.path.join(user_dir, "salary.xlsx")

# Khởi tạo file nếu chưa có
if not os.path.exists(excel_path):
    df_init = pd.DataFrame(columns=["Ngày", "Vị trí", "Thời gian", "Tổng lương", "Trạng thái", "Giờ vào", "Giờ ra"])
    df_init.to_excel(excel_path, index=False)

df = pd.read_excel(excel_path)
c_tt = find_col(df, "trạng thái") or find_col(df, "nhận") or "Trạng thái"
c_vt = find_col(df, "vị trí") or "Vị trí"
c_tl = find_col(df, "tổng lương") or "Tổng lương"
c_vao = find_col(df, "vào") or "Giờ vào"
c_ra = find_col(df, "ra") or "Giờ ra"

with st.sidebar:
    st.title(f"👤 {user}")
    if st.button("Đăng xuất"):
        del st.session_state.user
        st.rerun()
    
    with st.form("new_work"):
        st.write("### ➕ Thêm ca làm")
        vt_in = st.text_input("Vị trí làm")
        ng_in = st.date_input("Ngày", datetime.now())
        v_in = st.time_input("Vào")
        r_in = st.time_input("Ra")
        l_in = st.number_input("Lương/giờ", value=25000)
        tt_in = st.selectbox("Trạng thái", ["chưa nhận", "nhận"])
        if st.form_submit_button("Lưu ca làm"):
            tg = (datetime.combine(ng_in, r_in) - datetime.combine(ng_in, v_in)).total_seconds() / 3600
            new_row = {
                find_col(df, "ngày") or "Ngày": ng_in.strftime("%Y-%m-%d"),
                c_vt: vt_in, c_tl: tg*l_in, c_tt: tt_in,
                c_vao: v_in.strftime("%H:%M"), c_ra: r_in.strftime("%H:%M")
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_excel(excel_path, index=False)
            st.rerun()

# --- NỘI DUNG CHÍNH ---
st.header("💸 Thanh Toán Lương")

df_chua = df[df[c_tt].astype(str).str.lower().str.contains('chưa', na=False)].copy()

if not df_chua.empty:
    v_list = ["Tất cả"] + df_chua[c_vt].dropna().unique().tolist()
    chon = st.selectbox("Chọn vị trí để thanh toán:", v_list)
    f_df = df_chua if chon == "Tất cả" else df_chua[df_chua[c_vt] == chon]
    
    tong_no = pd.to_numeric(f_df[c_tl], errors='coerce').sum()
    st.error(f"💰 TỔNG TIỀN NỢ ({chon.upper()}): {tong_no:,.0f} VNĐ")

    ht = st.radio("Hình thức:", ["Chuyển khoản (QR)", "Tiền mặt"], horizontal=True)
    
    if ht == "Chuyển khoản (QR)":
        st.info("Quét mã để thanh toán")
        # (Phần hiện QR tương tự bản trước)
    else:
        if st.checkbox(f"Xác nhận đã cầm tiền mặt cho {len(f_df)} ca tại {chon}"):
            if st.button("🚀 Cập nhật tất cả thành 'Đã nhận'"):
                df.loc[f_df.index, c_tt] = "nhận"
                df.to_excel(excel_path, index=False)
                st.success("Đã thanh toán hàng loạt!")
                st.rerun()

    st.data_editor(f_df, use_container_width=True)
else:
    st.success("Hết nợ! 🎉")

st.write("### 📂 Toàn bộ dữ liệu")
st.dataframe(df)