import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from PIL import Image

# --- CẤU HÌNH ---
DB_FILE = "system_users.db"
STORAGE = "user_files"
if not os.path.exists(STORAGE): os.makedirs(STORAGE)

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT, qr_path TEXT)')
conn.commit()

def find_col(df, key):
    for col in df.columns:
        if key.lower() in str(col).lower(): return col
    return None

# --- ĐĂNG NHẬP ---
if 'user' not in st.session_state:
    st.title("🛡️ Hệ Thống Quản Lý Lương - Duy Trường")
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
user_dir = os.path.join(STORAGE, user)
if not os.path.exists(user_dir): os.makedirs(user_dir)
excel_path = os.path.join(user_dir, "salary.xlsx")

if not os.path.exists(excel_path):
    st.info("Hãy tải file Excel lên.")
    up = st.file_uploader("Chọn file .xlsx", type="xlsx")
    if up:
        tdf = pd.read_excel(up)
        if "Unnamed" in str(tdf.columns[0]): tdf = pd.read_excel(up, header=1)
        tdf.to_excel(excel_path, index=False)
        st.rerun()
    st.stop()

df = pd.read_excel(excel_path)
c_tt = find_col(df, "nhận")
c_vt = find_col(df, "vị trí")
c_tl = find_col(df, "tổng lương")
c_vao = find_col(df, "vào ca") or "giờ vào"
c_ra = find_col(df, "chốt ca") or "giờ ra"

# --- SIDEBAR: THÊM CA & CÀI ĐẶT ---
with st.sidebar:
    st.title(f"👤 {user}")
    if st.button("Đăng xuất"):
        del st.session_state.user
        st.rerun()
    
    with st.expander("🖼️ Cài đặt QR"):
        qr_img = st.file_uploader("Tải ảnh QR", type=['png','jpg','jpeg'])
        if qr_img:
            img = Image.open(qr_img)
            q_p = os.path.join(user_dir, "qr.png")
            img.save(q_p)
            c.execute('UPDATE users SET qr_path=? WHERE username=?', (q_p, user))
            conn.commit()
            st.success("Đã lưu QR!")

    with st.form("new_work"):
        st.write("### ➕ Thêm ca làm")
        vt_in = st.text_input("Vị trí làm")
        ng_in = st.date_input("Ngày")
        v_in = st.time_input("Vào")
        r_in = st.time_input("Ra")
        l_in = st.number_input("Lương/giờ", value=25000)
        tt_in = st.selectbox("Trạng thái", ["chưa nhận", "nhận"])
        if st.form_submit_button("Lưu ca làm"):
            tg = (datetime.combine(ng_in, r_in) - datetime.combine(ng_in, v_in)).total_seconds() / 3600
            new_row = {
                find_col(df, "ngày") or "Ngày": ng_in.strftime("%Y-%m-%d"),
                c_vt or "Vị trí": vt_in,
                c_tl or "tổng lương": tg*l_in,
                c_tt or "đã nhận lương chưa": tt_in,
                c_vao: v_in.strftime("%H:%M"),
                c_ra: r_in.strftime("%H:%M")
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_excel(excel_path, index=False)
            st.rerun()

# --- NỘI DUNG CHÍNH ---
st.header("💸 Quản Lý & Thanh Toán Lương")

if c_tt and c_vt and c_tl:
    df_chua = df[df[c_tt].astype(str).str.lower().str.contains('chưa', na=False)].copy()
    
    if not df_chua.empty:
        v_list = ["Tất cả"] + df_chua[c_vt].dropna().unique().tolist()
        chon = st.selectbox("Chọn vị trí để thanh toán:", v_list)
        f_df = df_chua if chon == "Tất cả" else df_chua[df_chua[c_vt] == chon]
        
        tong_no = pd.to_numeric(f_df[c_tl], errors='coerce').sum()
        st.error(f"💰 TỔNG TIỀN NỢ ({chon.upper()}): {tong_no:,.0f} VNĐ")

        # KHU VỰC THANH TOÁN
        st.subheader("💳 Hình thức thanh toán")
        ht = st.radio("Chọn phương thức:", ["Chuyển khoản (QR)", "Tiền mặt"], horizontal=True)
        
        if ht == "Chuyển khoản (QR)":
            if st.button("📩 Hiện mã QR để quét"):
                c.execute('SELECT qr_path FROM users WHERE username=?', (user,))
                res = c.fetchone()[0]
                if res and os.path.exists(res): st.image(res, width=250)
                else: st.warning("Hãy tải QR ở sidebar.")
        
        else: # TIỀN MẶT
            st.info("Bạn đang chọn thanh toán bằng Tiền mặt.")
            xac_nhan = st.checkbox("Xác nhận đã cầm tiền mặt (Tất cả ca của vị trí này sẽ thành 'Đã nhận')")
            if xac_nhan:
                if st.button(f"🚀 Cập nhật toàn bộ {len(f_df)} ca thành 'Đã nhận'"):
                    # Cập nhật trạng thái cho các dòng đang lọc
                    df.loc[f_df.index, c_tt] = "nhận"
                    df.to_excel(excel_path, index=False)
                    st.success("Đã thanh toán xong toàn bộ!")
                    st.rerun()

        st.divider()
        st.write("Hoặc sửa lẻ từng ca trong bảng:")
        edited = st.data_editor(f_df, use_container_width=True)
        if st.button("💾 Lưu chỉnh sửa lẻ"):
            df.update(edited)
            df.to_excel(excel_path, index=False)
            st.success("Đã cập nhật!")
            st.rerun()
    else:
        st.success("Hết nợ! 🎉")
else:
    st.error("File thiếu cột quan trọng.")

with st.expander("📂 Xem toàn bộ file"): st.dataframe(df)