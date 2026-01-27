import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from PIL import Image

# --- CẤU HÌNH HỆ THỐNG ---
DB_FILE = "system_users.db"
STORAGE = "user_files"
if not os.path.exists(STORAGE): os.makedirs(STORAGE)

# Kết nối Database (Tự tạo lại nếu bị Vercel xóa)
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT, qr_path TEXT)')
conn.commit()

# --- HÀM TÌM CỘT THÔNG MINH (SỬA LỖI GIỜ) ---
def find_col(df, keywords):
    """Tìm tên cột trong Excel dựa trên danh sách từ khóa"""
    if isinstance(keywords, str): keywords = [keywords] # Chuyển thành list nếu là string
    for col in df.columns:
        for key in keywords:
            if key.lower() in str(col).lower():
                return col
    return None

st.set_page_config(page_title="Quản Lý Lương - Duy Trường", layout="wide")

# --- PHẦN 1: MÀN HÌNH CHỜ (LOGIN / UPLOAD CỨU HỘ) ---
if 'user' not in st.session_state:
    st.title("🛡️ Hệ Thống Quản Lý Lương")
    
    t_log, t_reg, t_rescue = st.tabs(["Đăng nhập", "Đăng ký", "📂 Tải file cứu hộ"])
    
    with t_rescue:
        st.info("Dùng tab này nếu bạn bị mất tài khoản do web reset.")
        rescue_file = st.file_uploader("Tải file Excel cũ của bạn lên đây", type="xlsx")
        if rescue_file:
            st.session_state.temp_file = rescue_file
            st.success("Đã nhận file! Hãy qua tab Đăng ký/Đăng nhập để vào hệ thống.")

    with t_reg:
        u_reg = st.text_input("Tên đăng ký")
        p_reg = st.text_input("Mật khẩu mới", type='password')
        if st.button("Tạo tài khoản"):
            try:
                c.execute('INSERT INTO users(username, password) VALUES (?,?)', (u_reg, p_reg))
                conn.commit()
                st.success("Đăng ký thành công! Hãy đăng nhập.")
            except: st.error("Tên tài khoản đã tồn tại.")

    with t_log:
        u_log = st.text_input("Tên đăng nhập")
        p_log = st.text_input("Mật khẩu", type='password')
        if st.button("Vào hệ thống"):
            c.execute('SELECT * FROM users WHERE username=? AND password=?', (u_log, p_log))
            if c.fetchone():
                st.session_state.user = u_log
                # Xử lý file cứu hộ nếu có
                if 'temp_file' in st.session_state:
                    u_dir = os.path.join(STORAGE, u_log)
                    if not os.path.exists(u_dir): os.makedirs(u_dir)
                    with open(os.path.join(u_dir, "salary.xlsx"), "wb") as f:
                        f.write(st.session_state.temp_file.getbuffer())
                st.rerun()
            else: st.error("Sai thông tin đăng nhập.")
    st.stop()

# --- PHẦN 2: GIAO DIỆN CHÍNH (SAU KHI LOGIN) ---
user = st.session_state.user
user_dir = os.path.join(STORAGE, user)
if not os.path.exists(user_dir): os.makedirs(user_dir)
excel_path = os.path.join(user_dir, "salary.xlsx")

# Sidebar: Thông tin & Cài đặt
with st.sidebar:
    st.header(f"👤 {user}")
    if st.button("Đăng xuất"):
        del st.session_state.user
        st.rerun()
    
    st.divider()
    with st.expander("🖼️ Cài đặt QR Code"):
        qr_up = st.file_uploader("Tải ảnh QR ngân hàng", type=['png', 'jpg', 'jpeg'])
        if qr_up:
            img = Image.open(qr_up)
            qr_path = os.path.join(user_dir, "qr.png")
            img.save(qr_path)
            c.execute('UPDATE users SET qr_path=? WHERE username=?', (qr_path, user))
            conn.commit()
            st.success("Đã lưu mã QR!")

# Kiểm tra file dữ liệu
if not os.path.exists(excel_path):
    st.warning("⚠️ Chưa có dữ liệu. Vui lòng tải file Excel lên!")
    init_file = st.file_uploader("Chọn file .xlsx gốc", type="xlsx")
    if init_file:
        df_tmp = pd.read_excel(init_file)
        if "Unnamed" in str(df_tmp.columns[0]): df_tmp = pd.read_excel(init_file, header=1)
        df_tmp.to_excel(excel_path, index=False)
        st.rerun()
    st.stop()

# Đọc file và TỰ ĐỘNG DÒ CỘT (Phần quan trọng)
df = pd.read_excel(excel_path)

c_ngay = find_col(df, ["ngày", "date"]) or "Ngày"
c_vt = find_col(df, ["vị trí", "nơi", "location"]) or "Vị trí"
c_tl = find_col(df, ["tổng", "thành tiền", "lương"]) or "Tổng lương"
c_tt = find_col(df, ["trạng thái", "nhận", "status"]) or "Trạng thái"
# Dò nhiều từ khóa cho giờ vào/ra để không bị lỗi
c_vao = find_col(df, ["vào", "start", "in", "bắt đầu"]) or "Giờ vào"
c_ra = find_col(df, ["ra", "end", "out", "chốt", "kết thúc"]) or "Giờ ra"

# Sidebar: Thêm ca làm mới
with st.sidebar.form("add_new"):
    st.write("### ➕ Thêm ca làm việc")
    i_vt = st.text_input("Vị trí làm việc")
    i_ng = st.date_input("Ngày làm", datetime.now())
    i_v = st.time_input("Giờ vào")
    i_r = st.time_input("Giờ ra")
    i_luong = st.number_input("Lương/giờ", value=20000)
    i_tt = st.selectbox("Trạng thái", ["chưa nhận", "nhận"])
    
    if st.form_submit_button("Lưu ca làm"):
        # Tính giờ
        t_start = datetime.combine(i_ng, i_v)
        t_end = datetime.combine(i_ng, i_r)
        hours = (t_end - t_start).total_seconds() / 3600
        
        new_row = {
            c_ngay: i_ng.strftime("%Y-%m-%d"),
            c_vt: i_vt,
            c_tl: hours * i_luong,
            c_tt: i_tt,
            c_vao: i_v.strftime("%H:%M"), # Lưu đúng cột đã tìm thấy
            c_ra: i_r.strftime("%H:%M")   # Lưu đúng cột đã tìm thấy
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(excel_path, index=False)
        st.success(f"Đã thêm ca tại {i_vt}!")
        st.rerun()

# --- NỘI DUNG CHÍNH: QUẢN LÝ LƯƠNG ---
st.header("💸 Quản Lý & Thanh Toán")

# Lọc danh sách nợ
df_chua = df[df[c_tt].astype(str).str.lower().str.contains('chưa', na=False)].copy()

if not df_chua.empty:
    # Bộ lọc vị trí
    loc_list = ["Tất cả"] + df_chua[c_vt].dropna().unique().tolist()
    selected_loc = st.selectbox("🔍 Chọn vị trí cần thanh toán:", loc_list)
    
    # Dataframe hiển thị
    view_df = df_chua if selected_loc == "Tất cả" else df_chua[df_chua[c_vt] == selected_loc]
    
    # Tính tổng nợ
    total_debt = pd.to_numeric(view_df[c_tl], errors='coerce').sum()
    st.error(f"💰 TỔNG TIỀN NỢ ({selected_loc.upper()}): {total_debt:,.0f} VNĐ")

    # Khu vực thanh toán
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("💳 Chuyển khoản")
        if st.button("Hiện mã QR của tôi"):
            c.execute('SELECT qr_path FROM users WHERE username=?', (user,))
            res = c.fetchone()[0]
            if res and os.path.exists(res):
                st.image(res, caption=f"Mã QR của {user}", width=250)
            else:
                st.warning("Bạn chưa tải mã QR lên (xem thanh bên trái).")
    
    with c2:
        st.subheader("💵 Tiền mặt")
        if st.checkbox(f"Xác nhận đã nhận đủ tiền mặt ({selected_loc})"):
            if st.button("🚀 Cập nhật TẤT CẢ thành 'Đã nhận'"):
                # Update hàng loạt trong file gốc
                df.loc[view_df.index, c_tt] = "nhận"
                df.to_excel(excel_path, index=False)
                st.success("Đã thanh toán xong!")
                st.rerun()

    # Bảng chỉnh sửa chi tiết
    st.divider()
    st.write("📝 **Chỉnh sửa chi tiết từng ca:**")
    edited_df = st.data_editor(view_df, use_container_width=True)
    if st.button("💾 Lưu thay đổi bảng"):
        df.update(edited_df)
        df.to_excel(excel_path, index=False)
        st.success("Đã cập nhật dữ liệu!")
        st.rerun()
else:
    st.success("🎉 Tuyệt vời! Bạn không còn khoản nợ nào.")

# Xem toàn bộ dữ liệu & Tải về
st.divider()
with st.expander("📂 Xem toàn bộ lịch sử làm việc"):
    st.dataframe(df, use_container_width=True)

# Nút tải file dự phòng (Quan trọng cho Vercel)
st.download_button(
    label="📥 Tải file Excel về máy (Backup dữ liệu)",
    data=open(excel_path, "rb").read(),
    file_name="nhat_ky_luong_moi_nhat.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)