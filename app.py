import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from PIL import Image

# --- CẤU HÌNH ---
# ĐỔI TÊN DB ĐỂ TẠO LẠI BẢNG MỚI (FIX LỖI INDEX ERROR)
DB_FILE = "system_users_v2.db" 
STORAGE = "user_files"
if not os.path.exists(STORAGE): os.makedirs(STORAGE)

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# Tạo bảng users với đầy đủ thông tin: Zalo, Group
c.execute('''CREATE TABLE IF NOT EXISTS users
             (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
              qr_path TEXT, zalo_name TEXT, group_name TEXT)''')
conn.commit()

# --- HÀM TÌM CỘT ---
def find_col(df, keywords):
    if isinstance(keywords, str): keywords = [keywords]
    for col in df.columns:
        for key in keywords:
            if key.lower() in str(col).lower(): return col
    return None

# --- HÀM TÔ MÀU ---
def highlight_hours(val):
    try:
        hours = float(val)
        if hours >= 8: return 'background-color: #d4edda; color: green' 
        elif hours < 4 and hours > 0: return 'background-color: #f8d7da; color: red'
    except: pass
    return ''

st.set_page_config(page_title="Hệ Thống Giám Sát V2", layout="wide")

# --- PHẦN 1: ĐĂNG NHẬP / ĐĂNG KÝ ---
if 'user' not in st.session_state:
    st.title("🛡️ Hệ Thống Giám Sát & Lương (V2)")
    
    t_log, t_reg, t_res = st.tabs(["Đăng nhập", "Đăng ký", "Tải file cứu hộ"])
    
    with t_res:
        up = st.file_uploader("Tải file Excel cũ", type="xlsx")
        if up: st.session_state.temp_file = up

    with t_reg:
        st.caption("Tạo tài khoản mới (Dữ liệu cũ đã được reset để nâng cấp)")
        c1, c2 = st.columns(2)
        with c1: 
            u_r = st.text_input("Tên đăng nhập", key="reg_user")
            z_r = st.text_input("Tên Zalo", key="reg_zalo")
        with c2: 
            p_r = st.text_input("Mật khẩu", type='password', key="reg_pass")
            g_r = st.text_input("Tên Nhóm (Bếp, Bar...)", key="reg_group")
        
        r_r = st.radio("Vai trò:", ["Nhân viên", "Quản lý"], horizontal=True, key="reg_role")
        
        if st.button("Tạo tài khoản", key="btn_reg"):
            if u_r and p_r and z_r:
                try:
                    role = 'admin' if r_r == "Quản lý" else 'staff'
                    # Chèn đúng 6 cột dữ liệu
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?,?)', (u_r, p_r, role, None, z_r, g_r))
                    conn.commit()
                    st.success("Đăng ký thành công! Hãy chuyển qua tab Đăng nhập.")
                except sqlite3.IntegrityError:
                    st.error("Tên đăng nhập này đã tồn tại.")
                except Exception as e:
                    st.error(f"Lỗi hệ thống: {e}")
            else:
                st.warning("Vui lòng nhập đủ Tên đăng nhập, Mật khẩu và Tên Zalo")

    with t_log:
        u_l = st.text_input("Tên đăng nhập", key="log_user")
        p_l = st.text_input("Mật khẩu", type='password', key="log_pass")
        
        if st.button("Vào hệ thống", key="btn_login"):
            c.execute('SELECT * FROM users WHERE username=? AND password=?', (u_l, p_l))
            ud = c.fetchone()
            if ud:
                # Lấy dữ liệu an toàn hơn để tránh IndexError
                st.session_state.user = ud[0] # username
                st.session_state.role = ud[2] # role
                # Kiểm tra độ dài trước khi lấy zalo/group
                st.session_state.zalo = ud[4] if len(ud) > 4 else ud[0]
                st.session_state.group = ud[5] if len(ud) > 5 else ""
                
                # Nạp file cứu hộ
                if 'temp_file' in st.session_state:
                    p = os.path.join(STORAGE, u_l)
                    if not os.path.exists(p): os.makedirs(p)
                    with open(os.path.join(p, "salary.xlsx"), "wb") as f:
                        f.write(st.session_state.temp_file.getbuffer())
                st.rerun()
            else: st.error("Sai thông tin đăng nhập!")
    st.stop()

# --- LOGIC CHÍNH ---
user = st.session_state.user
role = st.session_state.role
zalo = st.session_state.zalo
group = st.session_state.group

with st.sidebar:
    st.title(f"👋 {zalo}")
    st.caption(f"Vai trò: {role.upper()} | Nhóm: {group}")
    if st.button("Đăng xuất"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# --- [QUẢN LÝ] TÍNH NĂNG THÔNG BÁO & CHECK-IN ---
if role == 'admin':
    st.header("🔔 Trung Tâm Điều Hành")
    
    # 1. HỆ THỐNG CẢNH BÁO
    now = datetime.now()
    alerts = []
    
    try:
        c.execute("SELECT username, zalo_name FROM users WHERE role='staff'")
        staffs = c.fetchall()
    except: staffs = []
    
    for s_id, s_name in staffs:
        p = os.path.join(STORAGE, s_id, "salary.xlsx")
        if os.path.exists(p):
            try:
                df_s = pd.read_excel(p)
                c_n = find_col(df_s, ["ngày"])
                c_v = find_col(df_s, ["vào", "start"])
                
                if c_n and c_v:
                    today_str = now.strftime("%Y-%m-%d")
                    shifts = df_s[df_s[c_n].astype(str).str.contains(today_str, na=False)]
                    for _, row in shifts.iterrows():
                        time_str = str(row[c_v])
                        try:
                            h, m = map(int, time_str.split(':')[:2])
                            shift_time = now.replace(hour=h, minute=m, second=0)
                            diff = (shift_time - now).total_seconds() / 60
                            if -15 < diff <= 60:
                                status = "SẮP VÀO CA" if diff > 0 else "ĐÃ TRỄ GIỜ"
                                alerts.append(f"⚠️ **{status} ({int(diff)}p nữa)**: {s_name} - Ca: {time_str}")
                        except: pass
            except: pass

    if alerts:
        st.warning("### 📲 CẦN GỌI NHÂN VIÊN NGAY!")
        for a in alerts: st.write(a)
    else:
        st.success("✅ Không có nhân viên nào sắp vào ca (trong 60p tới).")

    st.divider()

    # 2. XEM ĐIỂM DANH & XÁC NHẬN CÓ MẶT
    st.subheader("📅 Điểm Danh & Xác Nhận Có Mặt")
    col_d1, col_d2 = st.columns(2)
    with col_d1: view_date = st.date_input("Chọn ngày:", datetime.now())
    with col_d2: 
        if st.button("🔄 Tải lại dữ liệu"): st.rerun()

    daily_data = []
    
    for s_id, s_name in staffs:
        p = os.path.join(STORAGE, s_id, "salary.xlsx")
        if os.path.exists(p):
            try:
                dft = pd.read_excel(p)
                c_n = find_col(dft, ["ngày"])
                c_check = find_col(dft, ["xác nhận đến", "checkin"])
                
                if not c_check:
                    dft["Xác nhận đến"] = False
                    dft.to_excel(p, index=False)
                    c_check = "Xác nhận đến"

                if c_n:
                    day_str = view_date.strftime("%Y-%m-%d")
                    mask = dft[c_n].astype(str).str.contains(day_str, na=False)
                    worked = dft[mask]
                    
                    for idx, row in worked.iterrows():
                        c_vao = find_col(dft, ["vào"])
                        c_ra = find_col(dft, ["ra"])
                        hours = 0
                        try:
                            if c_vao and c_ra:
                                t1 = datetime.strptime(str(row[c_vao]), "%H:%M")
                                t2 = datetime.strptime(str(row[c_ra]), "%H:%M")
                                hours = (t2 - t1).total_seconds() / 3600
                        except: pass

                        daily_data.append({
                            "ID": s_id, "Tên": s_name,
                            "Vị trí": row.get(find_col(dft, ["vị trí"]), ""),
                            "Giờ vào": row.get(c_vao, ""), "Giờ ra": row.get(c_ra, ""),
                            "Số giờ": round(hours, 2), "Đã đến": row.get(c_check, False),
                            "File_Index": idx
                        })
            except: pass

    if daily_data:
        res_df = pd.DataFrame(daily_data)
        st.write("### Danh sách ca làm hôm nay")
        st.caption("✅ Tick vào ô 'Đã đến' để xác nhận nhân viên có mặt")
        
        edited_df = st.data_editor(
            res_df[["Tên", "Vị trí", "Giờ vào", "Giờ ra", "Số giờ", "Đã đến"]],
            column_config={
                "Đã đến": st.column_config.CheckboxColumn("Quản lý Xác nhận"),
                "Số giờ": st.column_config.NumberColumn("Số giờ làm", format="%.2f h")
            },
            disabled=["Tên", "Vị trí", "Giờ vào", "Giờ ra", "Số giờ"],
            hide_index=True,
        )
        
        if st.button("💾 Lưu xác nhận điểm danh"):
            for i, row in edited_df.iterrows():
                original = daily_data[i]
                if row["Đã đến"] != original["Đã đến"]:
                    u_p = os.path.join(STORAGE, original["ID"], "salary.xlsx")
                    u_df = pd.read_excel(u_p)
                    c_chk = find_col(u_df, ["xác nhận đến", "checkin"])
                    u_df.at[original["File_Index"], c_chk] = True
                    u_df.to_excel(u_p, index=False)
            st.success("Đã cập nhật trạng thái có mặt!")
            st.rerun()

        st.write("---")
        st.write("Phân loại giờ làm (Xanh: Đủ công, Đỏ: Thiếu công):")
        st.dataframe(res_df[["Tên", "Số giờ"]].style.applymap(highlight_hours, subset=["Số giờ"]), use_container_width=True)
    else:
        st.info("Chưa có ai đăng ký ca làm ngày này.")

# --- TÍNH NĂNG CHUNG (THÊM CA) ---
target_user = user 
if role == 'admin':
    st.divider()
    st.subheader("🔧 Công cụ Quản lý")
    target_input = st.text_input("Nhập ID nhân viên để thêm ca hộ:", placeholder="Bỏ trống nếu thêm cho chính mình")
    if target_input: target_user = target_input

p_target = os.path.join(STORAGE, target_user)
if not os.path.exists(p_target): os.makedirs(p_target)
path_excel = os.path.join(p_target, "salary.xlsx")

if not os.path.exists(path_excel):
    pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]).to_excel(path_excel, index=False)

df = pd.read_excel(path_excel)
c_tt = find_col(df, ["trạng thái", "nhận"]) or "Trạng thái"

with st.sidebar.form("add"):
    st.write(f"➕ Thêm ca cho: **{target_user}**")
    i_ng = st.date_input("Ngày", datetime.now())
    i_vt = st.text_input("Vị trí")
    c1, c2 = st.columns(2)
    with c1: i_v = st.time_input("Vào")
    with c2: i_r = st.time_input("Ra")
    i_l = st.number_input("Lương/h", value=20000)
    i_st = st.selectbox("Trạng thái", ["chưa nhận", "nhận"]) if role == 'staff' else "chưa nhận"
    
    if st.form_submit_button("Lưu"):
        t_start = datetime.combine(i_ng, i_v)
        t_end = datetime.combine(i_ng, i_r)
        h = (t_end - t_start).total_seconds() / 3600
        
        new = {
            find_col(df, ["ngày"]) or "Ngày": i_ng.strftime("%Y-%m-%d"),
            find_col(df, ["vị trí"]) or "Vị trí": i_vt,
            find_col(df, ["tổng", "lương"]) or "Tổng lương": h * i_l,
            c_tt: i_st,
            find_col(df, ["vào"]) or "Giờ vào": i_v.strftime("%H:%M"),
            find_col(df, ["ra"]) or "Giờ ra": i_r.strftime("%H:%M"),
            "Xác nhận đến": False
        }
        df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
        df.to_excel(path_excel, index=False)
        st.success("Đã thêm ca!")
        st.rerun()

if role == 'staff':
    st.header("📋 Bảng Lương Của Bạn")
    st.dataframe(df)