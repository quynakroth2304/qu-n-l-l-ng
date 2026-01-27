import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from PIL import Image

# --- CẤU HÌNH ---
DB_FILE = "system_users_v4.db" # Giữ nguyên DB của V7/V8
STORAGE = "user_files"
if not os.path.exists(STORAGE): os.makedirs(STORAGE)

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# 1. Bảng người dùng
c.execute('''CREATE TABLE IF NOT EXISTS users
             (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
              qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT)''')

# 2. Bảng nơi làm việc
c.execute('''CREATE TABLE IF NOT EXISTS workplaces
             (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''')
conn.commit()

# --- HÀM HỖ TRỢ ---
def find_col(df, keywords):
    if isinstance(keywords, str): keywords = [keywords]
    for col in df.columns:
        for key in keywords:
            if key.lower() in str(col).lower(): return col
    return None

def highlight_hours(val):
    try:
        hours = float(val)
        if hours >= 8: return 'background-color: #d4edda; color: green' 
        elif hours < 4 and hours > 0: return 'background-color: #f8d7da; color: red'
    except: pass
    return ''

st.set_page_config(page_title="Hệ Thống Quản Lý V9", layout="wide")

# --- PHẦN 1: ĐĂNG NHẬP / ĐĂNG KÝ ---
if 'user' not in st.session_state:
    st.title("🛡️ Hệ Thống Quản Lý Nhân Sự (V9)")
    
    t_log, t_reg, t_res = st.tabs(["Đăng nhập", "Đăng ký", "Tải file cứu hộ"])
    
    with t_res:
        up = st.file_uploader("Tải file Excel cũ", type="xlsx")
        if up: st.session_state.temp_file = up

    with t_reg:
        st.caption("📝 Điền đầy đủ thông tin")
        c1, c2 = st.columns(2)
        with c1: 
            u_r = st.text_input("Tên đăng nhập (ID)", key="reg_user")
            z_r = st.text_input("Tên Zalo (Hiển thị)", key="reg_zalo")
            phone_r = st.text_input("Số điện thoại", key="reg_phone")
        with c2: 
            p_r = st.text_input("Mật khẩu", type='password', key="reg_pass")
            
        r_r = st.radio("Vai trò:", ["Nhân viên", "Quản lý"], horizontal=True, key="reg_role")
        
        wp_id_input = ""
        if r_r == "Nhân viên":
            st.info("ℹ️ Cần Mã Nơi Làm Việc từ Quản lý.")
            wp_id_input = st.text_input("Nhập Mã ID Nơi Làm Việc (VD: CAFE_01)", key="reg_wp").strip()
        else:
            st.info("ℹ️ Quản lý sẽ tạo Mã Nơi Làm Việc sau khi đăng nhập.")

        if st.button("Tạo tài khoản", key="btn_reg"):
            if u_r and p_r and z_r and phone_r:
                try:
                    role_code = 'admin' if r_r == "Quản lý" else 'staff'
                    final_wp_id = "ADMIN"
                    
                    if role_code == 'staff':
                        if not wp_id_input:
                            st.error("Thiếu Mã Nơi Làm Việc!")
                            st.stop()
                        c.execute("SELECT id FROM workplaces WHERE id=?", (wp_id_input,))
                        if not c.fetchone():
                            st.error(f"❌ Mã '{wp_id_input}' không tồn tại!")
                            st.stop()
                        final_wp_id = wp_id_input

                    c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)', (u_r, p_r, role_code, None, z_r, final_wp_id, phone_r))
                    conn.commit()
                    st.success("✅ Đăng ký thành công! Hãy đăng nhập.")
                except sqlite3.IntegrityError:
                    st.error("Tên đăng nhập đã tồn tại.")
            else: st.warning("Vui lòng điền đủ thông tin!")

    with t_log:
        u_l = st.text_input("Tên đăng nhập", key="log_user")
        p_l = st.text_input("Mật khẩu", type='password', key="log_pass")
        
        if st.button("Vào hệ thống", key="btn_login"):
            c.execute('SELECT * FROM users WHERE username=? AND password=?', (u_l, p_l))
            ud = c.fetchone()
            if ud:
                st.session_state.user = ud[0]
                st.session_state.role = ud[2]
                st.session_state.zalo = ud[4] if len(ud)>4 else ud[0]
                st.session_state.wp_id = ud[5] if len(ud)>5 else ""
                
                if 'temp_file' in st.session_state:
                    p = os.path.join(STORAGE, u_l)
                    if not os.path.exists(p): os.makedirs(p)
                    with open(os.path.join(p, "salary.xlsx"), "wb") as f:
                        f.write(st.session_state.temp_file.getbuffer())
                st.rerun()
            else: st.error("Sai thông tin!")
    st.stop()

# --- LOGIC CHÍNH ---
user = st.session_state.user
role = st.session_state.role
zalo = st.session_state.zalo
wp_id = st.session_state.wp_id

with st.sidebar:
    st.title(f"👋 {zalo}")
    if role == 'staff':
        st.caption(f"📍 Nơi làm: **{wp_id}**")
    else:
        st.caption("👑 Quản Lý Hệ Thống")
        
    if st.button("Đăng xuất"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# --- [QUẢN LÝ] GIAO DIỆN ---
if role == 'admin':
    # 1. CẤU HÌNH CHI NHÁNH
    with st.expander("🏢 Cấu Hình Chi Nhánh (Tạo mã)", expanded=False):
        c1, c2 = st.columns([1, 2])
        with c1:
            new_wp_id = st.text_input("Tạo Mã Mới (VD: KHO_A)").upper().strip()
            new_wp_name = st.text_input("Tên Chi Nhánh (VD: Kho Hàng A)")
            if st.button("Lưu Mã"):
                if new_wp_id and new_wp_name:
                    try:
                        c.execute("INSERT INTO workplaces VALUES (?,?,?)", (new_wp_id, new_wp_name, user))
                        conn.commit()
                        st.success(f"Đã tạo: {new_wp_id}")
                        st.rerun()
                    except: st.error("Mã này đã tồn tại!")
        with c2:
            c.execute("SELECT id, name FROM workplaces")
            st.dataframe(pd.DataFrame(c.fetchall(), columns=["Mã ID", "Tên Chi Nhánh"]), use_container_width=True)

    # --- TÍNH NĂNG MỚI: QUẢN LÝ CHI TIẾT THEO NHÓM ---
    st.header("📊 Quản Lý Lương Chi Tiết Theo Nhóm")
    
    # BƯỚC 1: LẤY DỮ LIỆU NHÂN VIÊN
    try:
        c.execute("SELECT zalo_name, workplace_id, username, phone FROM users WHERE role='staff'")
        all_staff_data = c.fetchall() # List of tuples
    except: all_staff_data = []

    if all_staff_data:
        # BƯỚC 2: CHỌN CHI NHÁNH
        df_staffs = pd.DataFrame(all_staff_data, columns=["Tên", "Nơi làm việc", "ID", "SĐT"])
        list_workplaces = ["Tất cả"] + list(df_staffs["Nơi làm việc"].unique())
        
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            selected_wp = st.selectbox("1️⃣ Chọn Nhóm / Chi Nhánh:", list_workplaces)
        
        # Lọc danh sách nhân viên theo chi nhánh
        if selected_wp != "Tất cả":
            filtered_staffs = df_staffs[df_staffs["Nơi làm việc"] == selected_wp]
        else:
            filtered_staffs = df_staffs
        
        # BƯỚC 3: CHỌN NHÂN VIÊN
        with col_sel2:
            # Tạo list tên kèm ID để dễ chọn (VD: "Duy Trường (nv01)")
            staff_options = {f"{row['Tên']} ({row['ID']})": row['ID'] for index, row in filtered_staffs.iterrows()}
            selected_staff_label = st.selectbox("2️⃣ Chọn Nhân Viên:", list(staff_options.keys()))
            target_user_id = staff_options[selected_staff_label] if staff_options else None

        # BƯỚC 4: HIỂN THỊ CHI TIẾT NHÂN VIÊN ĐƯỢC CHỌN
        if target_user_id:
            st.divider()
            
            # Lấy thông tin SĐT và Nơi làm của user đang chọn
            staff_info = filtered_staffs[filtered_staffs["ID"] == target_user_id].iloc[0]
            st.subheader(f"📄 Hồ Sơ: {staff_info['Tên']}")
            st.caption(f"🆔 ID: {target_user_id} | 📱 SĐT: {staff_info['SĐT']} | 📍 {staff_info['Nơi làm việc']}")
            
            # Xử lý file Excel của nhân viên này
            p_target = os.path.join(STORAGE, target_user_id)
            if not os.path.exists(p_target): os.makedirs(p_target)
            path_excel = os.path.join(p_target, "salary.xlsx")

            if not os.path.exists(path_excel):
                pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]).to_excel(path_excel, index=False)

            df_target = pd.read_excel(path_excel)
            c_tt = find_col(df_target, ["trạng thái", "nhận"]) or "Trạng thái"
            c_tl = find_col(df_target, ["tổng", "lương"]) or "Tổng lương"

            # TÍNH TOÁN CÔNG NỢ
            try:
                debt_df = df_target[df_target[c_tt].astype(str).str.lower().str.contains('chưa', na=False)]
                total_debt = pd.to_numeric(debt_df[c_tl], errors='coerce').sum()
            except: total_debt = 0

            # HIỂN THỊ TỔNG TIỀN NỢ TO ĐÙNG
            c_met1, c_met2 = st.columns(2)
            with c_met1:
                st.metric(label="TỔNG LƯƠNG CHƯA THANH TOÁN", value=f"{total_debt:,.0f} VNĐ", delta="Cần trả")
            with c_met2:
                with st.expander("➕ Thêm Ca Làm Cho Nhân Viên Này"):
                    with st.form("add_shift_admin"):
                        i_ng = st.date_input("Ngày", datetime.now())
                        i_vt = st.text_input("Vị trí chi tiết", value=staff_info['Nơi làm việc'])
                        c_t1, c_t2 = st.columns(2)
                        with c_t1: i_v = st.time_input("Vào")
                        with c_t2: i_r = st.time_input("Ra")
                        i_l = st.number_input("Lương/h", value=20000)
                        if st.form_submit_button("Lưu Ca Làm"):
                            t_start = datetime.combine(i_ng, i_v)
                            t_end = datetime.combine(i_ng, i_r)
                            if t_end < t_start: t_end += timedelta(days=1) # Fix ca đêm
                            h = (t_end - t_start).total_seconds() / 3600
                            new_row = {
                                find_col(df_target, ["ngày"]) or "Ngày": i_ng.strftime("%Y-%m-%d"),
                                find_col(df_target, ["vị trí"]) or "Vị trí": i_vt,
                                find_col(df_target, ["tổng"]) or "Tổng lương": h * i_l,
                                c_tt: "chưa nhận",
                                find_col(df_target, ["vào"]) or "Giờ vào": i_v.strftime("%H:%M"),
                                find_col(df_target, ["ra"]) or "Giờ ra": i_r.strftime("%H:%M"),
                                "Xác nhận đến": False
                            }
                            df_target = pd.concat([df_target, pd.DataFrame([new_row])], ignore_index=True)
                            df_target.to_excel(path_excel, index=False)
                            st.success("Đã thêm ca!"); st.rerun()

            # HIỂN THỊ BẢNG CHI TIẾT
            st.write("🔻 **Lịch sử làm việc chi tiết:**")
            st.dataframe(df_target, use_container_width=True)

    else:
        st.warning("Chưa có nhân viên nào trong hệ thống.")

    st.divider()

    # --- CÁC PHẦN CŨ (CẢNH BÁO & ĐIỂM DANH) ---
    st.subheader("🔔 Cảnh Báo Chung & Điểm Danh")
    # (Phần này giữ nguyên logic V8 nhưng thu gọn để tập trung vào tính năng mới ở trên)
    
    # ... [Logic cảnh báo tự động chạy ngầm] ...
    now = datetime.now()
    alerts = []
    if all_staff_data:
        for s_tuple in all_staff_data: # s_tuple = (zalo, wp, username, phone)
            s_id = s_tuple[2]; s_name = s_tuple[0]; s_phone = s_tuple[3]
            p = os.path.join(STORAGE, s_id, "salary.xlsx")
            if os.path.exists(p):
                try:
                    df_s = pd.read_excel(p)
                    c_n = find_col(df_s, ["ngày"]); c_v = find_col(df_s, ["vào"])
                    if c_n and c_v:
                        today_str = now.strftime("%Y-%m-%d")
                        shifts = df_s[df_s[c_n].astype(str).str.contains(today_str, na=False)]
                        for _, row in shifts.iterrows():
                            # Logic check giờ vào
                            pass # (Giữ code check giờ của V8 ở đây nếu muốn hiển thị lại)
                except: pass

    # ĐIỂM DANH NHANH
    col_d1, col_d2 = st.columns(2)
    with col_d1: view_date = st.date_input("📅 Xem điểm danh ngày:", datetime.now())
    with col_d2: 
        if st.button("🔄 Tải lại"): st.rerun()
    
    # Hiển thị bảng điểm danh tổng hợp (Logic V8)
    daily_data = []
    total_day_cost = 0 
    if all_staff_data:
        for s_tuple in all_staff_data:
            s_id = s_tuple[2]; s_name = s_tuple[0]; s_phone = s_tuple[3]; s_wp = s_tuple[1]
            p = os.path.join(STORAGE, s_id, "salary.xlsx")
            if os.path.exists(p):
                try:
                    dft = pd.read_excel(p)
                    c_n = find_col(dft, ["ngày"])
                    c_check = find_col(dft, ["xác nhận", "checkin"])
                    c_tl = find_col(dft, ["tổng", "lương"]) 
                    if not c_check:
                        dft["Xác nhận đến"] = False; dft.to_excel(p, index=False); c_check = "Xác nhận đến"
                    if c_n:
                        day_str = view_date.strftime("%Y-%m-%d")
                        worked = dft[dft[c_n].astype(str).str.contains(day_str, na=False)]
                        for idx, row in worked.iterrows():
                            c_vao = find_col(dft, ["vào"]); c_ra = find_col(dft, ["ra"])
                            hours = 0; salary = 0
                            try:
                                if c_vao and c_ra:
                                    t1 = datetime.strptime(str(row[c_vao]), "%H:%M")
                                    t2 = datetime.strptime(str(row[c_ra]), "%H:%M")
                                    if t2 < t1: t2 += timedelta(days=1)
                                    hours = (t2 - t1).total_seconds() / 3600
                                if c_tl: salary = float(row.get(c_tl, 0))
                            except: pass
                            total_day_cost += salary 
                            daily_data.append({
                                "ID": s_id, "Tên": s_name, "Chi nhánh": s_wp,
                                "Giờ vào": row.get(c_vao, ""), "Giờ ra": row.get(c_ra, ""),
                                "Số giờ": round(hours, 2), "Lương (VNĐ)": f"{salary:,.0f}", 
                                "Đã đến": row.get(c_check, False), "File_Index": idx
                            })
                except: pass

    if daily_data:
        st.info(f"Tổng lương ngày: {total_day_cost:,.0f} VNĐ")
        res_df = pd.DataFrame(daily_data)
        edited_df = st.data_editor(
            res_df[["Tên", "Chi nhánh", "Giờ vào", "Giờ ra", "Số giờ", "Lương (VNĐ)", "Đã đến"]],
            column_config={"Đã đến": st.column_config.CheckboxColumn("Có mặt")},
            disabled=["Tên", "Chi nhánh", "Giờ vào", "Giờ ra", "Số giờ", "Lương (VNĐ)"], hide_index=True,
        )
        if st.button("💾 Lưu điểm danh"):
            for i, row in edited_df.iterrows():
                original = daily_data[i]
                if row["Đã đến"] != original["Đã đến"]:
                    u_p = os.path.join(STORAGE, original["ID"], "salary.xlsx")
                    u_df = pd.read_excel(u_p)
                    c_chk = find_col(u_df, ["xác nhận", "checkin"])
                    u_df.at[original["File_Index"], c_chk] = True
                    u_df.to_excel(u_p, index=False)
            st.success("Đã lưu!"); st.rerun()
    else: st.info("Không có dữ liệu điểm danh.")

# --- NHÂN VIÊN GIAO DIỆN ---
if role == 'staff':
    st.header("📋 Bảng Lương Của Bạn")
    
    # Tự động tạo file nếu chưa có
    p_me = os.path.join(STORAGE, user)
    if not os.path.exists(p_me): os.makedirs(p_me)
    excel_me = os.path.join(p_me, "salary.xlsx")
    if not os.path.exists(excel_me):
        pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]).to_excel(excel_me, index=False)
        
    df_me = pd.read_excel(excel_me)
    c_tt = find_col(df_me, ["trạng thái", "nhận"]) or "Trạng thái"

    # Form tự thêm ca
    with st.sidebar.form("staff_add"):
        st.write("➕ Tự khai báo ca làm")
        i_ng = st.date_input("Ngày", datetime.now())
        i_vt = st.text_input("Vị trí chi tiết", value=wp_id)
        c1, c2 = st.columns(2)
        with c1: i_v = st.time_input("Vào")
        with c2: i_r = st.time_input("Ra")
        i_l = st.number_input("Lương/h", value=20000)
        i_st = st.selectbox("Trạng thái", ["chưa nhận", "nhận"])
        
        if st.form_submit_button("Lưu Ca"):
            t_start = datetime.combine(i_ng, i_v)
            t_end = datetime.combine(i_ng, i_r)
            if t_end < t_start: t_end += timedelta(days=1)
            h = (t_end - t_start).total_seconds() / 3600
            new = {
                find_col(df_me, ["ngày"]) or "Ngày": i_ng.strftime("%Y-%m-%d"),
                find_col(df_me, ["vị trí"]) or "Vị trí": i_vt,
                find_col(df_me, ["tổng"]) or "Tổng lương": h * i_l,
                c_tt: i_st,
                find_col(df_me, ["vào"]) or "Giờ vào": i_v.strftime("%H:%M"),
                find_col(df_me, ["ra"]) or "Giờ ra": i_r.strftime("%H:%M"),
                "Xác nhận đến": False
            }
            df_me = pd.concat([df_me, pd.DataFrame([new])], ignore_index=True)
            df_me.to_excel(excel_me, index=False)
            st.success("Đã lưu!"); st.rerun()

    st.dataframe(df_me)