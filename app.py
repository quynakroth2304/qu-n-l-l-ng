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

# Kết nối Database & Tự động Migration (Thêm cột mới nếu chưa có)
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# Tạo bảng users với đầy đủ thông tin: Zalo, Group
c.execute('''CREATE TABLE IF NOT EXISTS users
             (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
              qr_path TEXT, zalo_name TEXT, group_name TEXT)''')
conn.commit()

# --- HÀM TÌM CỘT THÔNG MINH ---
def find_col(df, keywords):
    if isinstance(keywords, str): keywords = [keywords]
    for col in df.columns:
        for key in keywords:
            if key.lower() in str(col).lower(): return col
    return None

st.set_page_config(page_title="Hệ Thống Chấm Công Nhóm", layout="wide")

# --- PHẦN 1: ĐĂNG NHẬP / ĐĂNG KÝ ---
if 'user' not in st.session_state:
    st.title("🛡️ Hệ Thống Chấm Công & Lương")
    
    t_log, t_reg, t_rescue = st.tabs(["Đăng nhập", "Đăng ký thành viên", "📂 Tải file cứu hộ"])
    
    with t_rescue:
        st.info("Dùng khi bị mất dữ liệu tạm thời.")
        res = st.file_uploader("Tải file Excel cũ", type="xlsx")
        if res: st.session_state.temp_file = res

    with t_reg:
        st.write("📝 **Đăng ký thành viên mới**")
        c1, c2 = st.columns(2)
        with c1: 
            u_reg = st.text_input("Tên đăng nhập (ID duy nhất)")
            zalo_reg = st.text_input("Tên hiển thị Zalo (Để tránh nhầm lẫn)")
        with c2: 
            p_reg = st.text_input("Mật khẩu", type='password')
            group_reg = st.text_input("Tên Nhóm (VD: Cafe, Bếp, Kho...)")
        
        role_reg = st.radio("Vai trò:", ["Nhân viên", "Quản lý"], horizontal=True)
        
        if st.button("Tạo tài khoản"):
            if u_reg and p_reg and zalo_reg and group_reg:
                try:
                    r_code = 'admin' if role_reg == "Quản lý" else 'staff'
                    c.execute('INSERT INTO users(username, password, role, zalo_name, group_name) VALUES (?,?,?,?,?)', 
                              (u_reg, p_reg, r_code, zalo_reg, group_reg))
                    conn.commit()
                    st.success(f"Đã tạo tài khoản cho {zalo_reg} thuộc nhóm {group_reg}!")
                except: st.error("ID đăng nhập này đã tồn tại.")
            else: st.warning("Vui lòng điền đầy đủ thông tin!")

    with t_log:
        u_log = st.text_input("Tên đăng nhập")
        p_log = st.text_input("Mật khẩu", type='password')
        if st.button("Vào hệ thống"):
            c.execute('SELECT * FROM users WHERE username=? AND password=?', (u_log, p_log))
            ud = c.fetchone()
            if ud:
                st.session_state.user = u_log
                st.session_state.role = ud[2] if len(ud) > 2 else 'staff'
                st.session_state.zalo = ud[4] if len(ud) > 4 else u_log
                st.session_state.group = ud[5] if len(ud) > 5 else 'Chưa phân nhóm'
                
                # Nạp file cứu hộ
                if 'temp_file' in st.session_state:
                    u_dir = os.path.join(STORAGE, u_log)
                    if not os.path.exists(u_dir): os.makedirs(u_dir)
                    with open(os.path.join(u_dir, "salary.xlsx"), "wb") as f:
                        f.write(st.session_state.temp_file.getbuffer())
                st.rerun()
            else: st.error("Sai thông tin!")
    st.stop()

# --- PHẦN 2: LOGIC CHÍNH ---
current_user = st.session_state.user
current_role = st.session_state.role
current_zalo = st.session_state.zalo
current_group = st.session_state.group

# Sidebar
with st.sidebar:
    st.title(f"👋 {current_zalo}")
    st.caption(f"ID: {current_user} | Nhóm: {current_group}")
    st.caption(f"Vai trò: {'👑 QUẢN LÝ' if current_role == 'admin' else '👤 NHÂN VIÊN'}")
    if st.button("Đăng xuất"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- CHỨC NĂNG QUẢN LÝ (ADMIN) ---
if current_role == 'admin':
    st.header("👑 Bảng Điều Khiển Quản Lý")
    tab1, tab2 = st.tabs(["📅 Điểm danh theo ngày", "🔍 Quản lý từng nhân viên"])
    
    # TAB 1: XEM TỔNG QUÁT THEO NGÀY (TÍNH NĂNG MỚI)
    with tab1:
        st.subheader("Ai đi làm hôm nay?")
        col_d1, col_d2 = st.columns(2)
        with col_d1: view_date = st.date_input("Chọn ngày xem:", datetime.now())
        with col_d2: 
            # Lấy danh sách các nhóm
            c.execute("SELECT DISTINCT group_name FROM users WHERE group_name IS NOT NULL")
            groups = [row[0] for row in c.fetchall()]
            view_group = st.selectbox("Lọc theo nhóm:", ["Tất cả"] + groups)

        if st.button("Quét dữ liệu chấm công"):
            # Lấy danh sách nhân viên
            query = "SELECT username, zalo_name, group_name FROM users WHERE role='staff'"
            if view_group != "Tất cả": query += f" AND group_name='{view_group}'"
            c.execute(query)
            staffs = c.fetchall()
            
            daily_report = []
            for s_id, s_zalo, s_group in staffs:
                path = os.path.join(STORAGE, s_id, "salary.xlsx")
                if os.path.exists(path):
                    try:
                        dft = pd.read_excel(path)
                        # Tìm cột ngày
                        c_n = find_col(dft, ["ngày", "date"])
                        c_v = find_col(dft, ["vào", "start"])
                        c_r = find_col(dft, ["ra", "end"])
                        c_vt = find_col(dft, ["vị trí", "nơi"])
                        
                        if c_n:
                            # Lọc ra dòng có ngày trùng khớp
                            day_str = view_date.strftime("%Y-%m-%d")
                            mask = dft[c_n].astype(str).str.contains(day_str, na=False)
                            worked = dft[mask]
                            
                            for _, row in worked.iterrows():
                                daily_report.append({
                                    "Tên Zalo": s_zalo,
                                    "Nhóm": s_group,
                                    "Vị trí làm": row.get(c_vt, ""),
                                    "Giờ vào": row.get(c_v, ""),
                                    "Giờ ra": row.get(c_r, ""),
                                    "ID": s_id
                                })
                    except: pass
            
            if daily_report:
                st.dataframe(pd.DataFrame(daily_report))
            else:
                st.info(f"Không tìm thấy dữ liệu chấm công ngày {view_date.strftime('%d/%m/%Y')}")

    # TAB 2: QUẢN LÝ CHI TIẾT (Logic cũ)
    with tab2:
        target_id = st.text_input("Nhập ID nhân viên cần xem:", placeholder="Ví dụ: nv01")
        if target_id:
            c.execute("SELECT zalo_name, group_name FROM users WHERE username=?", (target_id,))
            info = c.fetchone()
            if info:
                st.success(f"Đang xem: **{info[0]}** (Nhóm: {info[1]})")
                target_user = target_id
            else:
                st.error("Không tìm thấy nhân viên này.")
                target_user = None
        else: target_user = None

# --- CHỨC NĂNG NHÂN VIÊN (STAFF) ---
else:
    target_user = current_user # Nhân viên tự xem chính mình

# --- XỬ LÝ FILE EXCEL CỦA USER ĐƯỢC CHỌN ---
if target_user:
    u_path = os.path.join(STORAGE, target_user)
    if not os.path.exists(u_path): os.makedirs(u_path)
    excel_path = os.path.join(u_path, "salary.xlsx")
    
    # Tạo file nếu chưa có
    if not os.path.exists(excel_path):
        pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái"]).to_excel(excel_path, index=False)
    
    df = pd.read_excel(excel_path)
    
    # Tìm cột
    c_ngay = find_col(df, ["ngày", "date"]) or "Ngày"
    c_vt = find_col(df, ["vị trí", "nơi"]) or "Vị trí"
    c_tl = find_col(df, ["tổng", "lương"]) or "Tổng lương"
    c_tt = find_col(df, ["trạng thái", "nhận"]) or "Trạng thái"
    c_vao = find_col(df, ["vào", "start"]) or "Giờ vào"
    c_ra = find_col(df, ["ra", "end"]) or "Giờ ra"

    # FORM THÊM CA (Cả Quản lý và Nhân viên đều dùng được)
    with st.sidebar.form("add"):
        st.write(f"### ➕ Thêm ca: {target_user}")
        i_ng = st.date_input("Ngày", datetime.now())
        i_vt = st.text_input("Vị trí làm")
        c1, c2 = st.columns(2)
        with c1: i_v = st.time_input("Vào")
        with c2: i_r = st.time_input("Ra")
        i_l = st.number_input("Lương/h", value=20000)
        
        # Nếu là Admin thì mặc định chưa nhận, Staff thì được chọn
        if current_role == 'admin': i_tt = "chưa nhận"
        else: i_tt = st.selectbox("Trạng thái", ["chưa nhận", "nhận"])

        if st.form_submit_button("Lưu ca"):
            tg = (datetime.combine(i_ng, i_r) - datetime.combine(i_ng, i_v)).total_seconds() / 3600
            row = {
                c_ngay: i_ng.strftime("%Y-%m-%d"),
                c_vt: i_vt, c_tl: tg*i_l, c_tt: i_tt,
                c_vao: i_v.strftime("%H:%M"), c_ra: i_r.strftime("%H:%M")
            }
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            df.to_excel(excel_path, index=False)
            st.success("Đã lưu!")
            st.rerun()

    # HIỂN THỊ BẢNG LƯƠNG
    if current_role == 'admin' and tab1.title == "📅 Điểm danh theo ngày":
         pass # Nếu đang ở Tab điểm danh thì không hiện bảng chi tiết ở dưới làm rối
    else:
        st.divider()
        st.subheader(f"📋 Bảng lương chi tiết")
        
        # Lọc nợ
        df_chua = df[df[c_tt].astype(str).str.lower().str.contains('chưa', na=False)].copy()
        
        if not df_chua.empty:
            gr_loc = ["Tất cả"] + df_chua[c_vt].dropna().unique().tolist()
            chon = st.selectbox("Lọc vị trí thanh toán:", gr_loc)
            v_df = df_chua if chon == "Tất cả" else df_chua[df_chua[c_vt] == chon]
            
            t_no = pd.to_numeric(v_df[c_tl], errors='coerce').sum()
            st.error(f"💰 TỔNG NỢ ({chon}): {t_no:,.0f} VNĐ")
            
            # Chỉ nhân viên mới được xác nhận nhận tiền
            if current_role == 'staff':
                if st.button("🚀 Xác nhận đã nhận TIỀN MẶT (Toàn bộ)"):
                    df.loc[v_df.index, c_tt] = "nhận"
                    df.to_excel(excel_path, index=False)
                    st.rerun()
                
                # Nút sửa
                edited = st.data_editor(v_df, use_container_width=True)
                if st.button("Lưu sửa đổi"):
                    df.update(edited)
                    df.to_excel(excel_path, index=False)
                    st.rerun()
            else:
                st.dataframe(v_df, use_container_width=True)
        else:
            st.success("Đã thanh toán hết!")

        with st.expander("Lịch sử toàn bộ"):
            st.dataframe(df, use_container_width=True)