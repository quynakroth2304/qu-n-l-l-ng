import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from PIL import Image

# --- CẤU HÌNH ---
DB_FILE = "system_users_v4.db" 
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

st.set_page_config(page_title="Hệ Thống Quản Lý V8", layout="wide")

# --- PHẦN 1: ĐĂNG NHẬP / ĐĂNG KÝ ---
if 'user' not in st.session_state:
    st.title("🛡️ Hệ Thống Quản Lý Nhân Sự (V8)")
    
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
            phone_r = st.text_input("Số điện thoại liên hệ", key="reg_phone")
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
    # 1. QUẢN LÝ MÃ LÀM VIỆC
    with st.expander("🏢 CẤU HÌNH CHI NHÁNH & MÃ LÀM VIỆC", expanded=False):
        c1, c2 = st.columns([1, 2])
        with c1:
            new_wp_id = st.text_input("Tạo Mã ID Mới (VD: KHO_A)").upper().strip()
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
            st.write("📋 **Mã đang hoạt động**")
            c.execute("SELECT id, name FROM workplaces")
            st.dataframe(pd.DataFrame(c.fetchall(), columns=["Mã ID", "Tên Chi Nhánh"]), use_container_width=True)

    # 2. DANH SÁCH THÀNH VIÊN
    st.header("👥 Danh Sách Thành Viên")
    try:
        c.execute("SELECT zalo_name, phone, workplace_id, username FROM users WHERE role='staff'")
        all_staffs = c.fetchall()
        if all_staffs:
            df_staffs = pd.DataFrame(all_staffs, columns=["Họ và Tên", "Số Điện Thoại", "Nơi Làm Việc", "ID Tài Khoản"])
            wp_filter_list = ["Tất cả"] + list(df_staffs["Nơi Làm Việc"].unique())
            selected_wp = st.selectbox("Lọc theo Chi nhánh:", wp_filter_list)
            
            if selected_wp != "Tất cả": df_show = df_staffs[df_staffs["Nơi Làm Việc"] == selected_wp]
            else: df_show = df_staffs
            
            st.dataframe(df_show, use_container_width=True, column_config={"Số Điện Thoại": st.column_config.TextColumn("SĐT Liên Hệ")})
        else: st.info("Chưa có nhân viên.")
    except: pass

    st.divider()
    
    # 3. TRUNG TÂM CẢNH BÁO
    st.subheader("🔔 Trung Tâm Cảnh Báo & Công Nợ")
    
    now = datetime.now()
    alerts = []
    total_system_debt = 0 
    
    for s_name, s_phone, s_wp, s_id in all_staffs:
        p = os.path.join(STORAGE, s_id, "salary.xlsx")
        if os.path.exists(p):
            try:
                df_s = pd.read_excel(p)
                c_n = find_col(df_s, ["ngày"])
                c_v = find_col(df_s, ["vào", "start"])
                c_tt = find_col(df_s, ["trạng thái", "nhận"])
                c_tl = find_col(df_s, ["tổng", "lương"])
                
                # Cảnh báo giờ làm (Xử lý cả ca đêm)
                if c_n and c_v:
                    today_str = now.strftime("%Y-%m-%d")
                    shifts = df_s[df_s[c_n].astype(str).str.contains(today_str, na=False)]
                    for _, row in shifts.iterrows():
                        time_str = str(row[c_v])
                        try:
                            h, m = map(int, time_str.split(':')[:2])
                            shift_time = now.replace(hour=h, minute=m, second=0)
                            # Logic cảnh báo đơn giản
                            diff = (shift_time - now).total_seconds() / 60
                            if -15 < diff <= 60:
                                status = "SẮP VÀO CA" if diff > 0 else "ĐÃ TRỄ GIỜ"
                                alerts.append(f"⚠️ **{status} ({int(diff)}p)**: {s_name} - SĐT: {s_phone}")
                        except: pass
                
                # Tổng nợ
                if c_tt and c_tl:
                    debt_rows = df_s[df_s[c_tt].astype(str).str.lower().str.contains('chưa', na=False)]
                    total_system_debt += pd.to_numeric(debt_rows[c_tl], errors='coerce').sum()
            except: pass

    c_m1, c_m2 = st.columns(2)
    with c_m1: st.metric("TỔNG NỢ LƯƠNG TOÀN HỆ THỐNG", f"{total_system_debt:,.0f} VNĐ")
    with c_m2:
        if alerts:
            st.error(f"Có {len(alerts)} cảnh báo!")
            with st.expander("📲 Xem chi tiết", expanded=True):
                for a in alerts: st.write(a)
        else: st.success("Không có cảnh báo giờ làm.")

    st.divider()

    # 4. ĐIỂM DANH (XỬ LÝ CA ĐÊM TRONG HIỂN THỊ)
    st.subheader("📅 Điểm Danh Hôm Nay")
    c_f1, c_f2 = st.columns(2)
    with c_f1: view_date = st.date_input("Ngày:", datetime.now())
    with c_f2: 
        if st.button("🔄 Cập nhật"): st.rerun()

    daily_data = []
    total_day_cost = 0 
    
    for s_name, s_phone, s_wp, s_id in all_staffs:
        p = os.path.join(STORAGE, s_id, "salary.xlsx")
        if os.path.exists(p):
            try:
                dft = pd.read_excel(p)
                c_n = find_col(dft, ["ngày"])
                c_check = find_col(dft, ["xác nhận", "checkin"])
                c_tl = find_col(dft, ["tổng", "lương"]) 
                
                if not c_check:
                    dft["Xác nhận đến"] = False
                    dft.to_excel(p, index=False)
                    c_check = "Xác nhận đến"

                if c_n:
                    day_str = view_date.strftime("%Y-%m-%d")
                    worked = dft[dft[c_n].astype(str).str.contains(day_str, na=False)]
                    
                    for idx, row in worked.iterrows():
                        c_vao = find_col(dft, ["vào"])
                        c_ra = find_col(dft, ["ra"])
                        hours = 0; salary = 0
                        try:
                            # TÍNH GIỜ (FIX CA ĐÊM HIỂN THỊ)
                            if c_vao and c_ra:
                                t1 = datetime.strptime(str(row[c_vao]), "%H:%M")
                                t2 = datetime.strptime(str(row[c_ra]), "%H:%M")
                                if t2 < t1: # Ca qua đêm
                                    t2 += timedelta(days=1)
                                hours = (t2 - t1).total_seconds() / 3600
                                
                            if c_tl: salary = float(row.get(c_tl, 0))
                        except: pass
                        
                        total_day_cost += salary 
                        daily_data.append({
                            "ID": s_id, "Tên": s_name, "SĐT": s_phone, "Chi nhánh": s_wp,
                            "Giờ vào": row.get(c_vao, ""), "Giờ ra": row.get(c_ra, ""),
                            "Số giờ": round(hours, 2), "Lương (VNĐ)": f"{salary:,.0f}", 
                            "Đã đến": row.get(c_check, False), "File_Index": idx
                        })
            except: pass

    if daily_data:
        st.info(f"💵 Lương ngày {view_date.strftime('%d/%m')}: **{total_day_cost:,.0f} VNĐ**")
        res_df = pd.DataFrame(daily_data)
        edited_df = st.data_editor(
            res_df[["Tên", "SĐT", "Chi nhánh", "Giờ vào", "Giờ ra", "Số giờ", "Lương (VNĐ)", "Đã đến"]],
            column_config={"Đã đến": st.column_config.CheckboxColumn("Có mặt"), "Số giờ": st.column_config.NumberColumn(format="%.2f h")},
            disabled=["Tên", "SĐT", "Chi nhánh", "Giờ vào", "Giờ ra", "Số giờ", "Lương (VNĐ)"], hide_index=True,
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
        st.dataframe(res_df[["Tên", "Số giờ"]].style.applymap(highlight_hours, subset=["Số giờ"]), use_container_width=True)
    else: st.info("Không có dữ liệu.")

# --- TÍNH NĂNG CHUNG ---
target_user = user 
if role == 'admin':
    st.divider()
    st.subheader("🔧 Công cụ Cá Nhân")
    target_input = st.text_input("Nhập ID nhân viên:", placeholder="Ví dụ: nv01")
    if target_input: target_user = target_input

p_target = os.path.join(STORAGE, target_user)
if not os.path.exists(p_target): os.makedirs(p_target)
path_excel = os.path.join(p_target, "salary.xlsx")

if not os.path.exists(path_excel):
    pd.DataFrame(columns=["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]).to_excel(path_excel, index=False)

df = pd.read_excel(path_excel)
c_tt = find_col(df, ["trạng thái", "nhận"]) or "Trạng thái"

with st.sidebar.form("add"):
    st.write(f"➕ Thêm ca: **{target_user}**")
    i_ng = st.date_input("Ngày", datetime.now())
    i_vt = st.text_input("Vị trí chi tiết")
    c1, c2 = st.columns(2)
    with c1: i_v = st.time_input("Vào")
    with c2: i_r = st.time_input("Ra")
    i_l = st.number_input("Lương/h", value=20000)
    i_st = st.selectbox("Trạng thái", ["chưa nhận", "nhận"]) if role == 'staff' else "chưa nhận"
    
    if st.form_submit_button("Lưu"):
        # --- FIX LỖI CA ĐÊM (SỐ ÂM) ---
        t_start = datetime.combine(i_ng, i_v)
        t_end = datetime.combine(i_ng, i_r)
        
        # Nếu Giờ ra < Giờ vào -> Hiểu là sang ngày hôm sau
        if t_end < t_start:
            t_end += timedelta(days=1) # Cộng thêm 1 ngày
            
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
        st.success("Đã thêm ca (Tự động xử lý ca đêm)!"); st.rerun()

if role == 'staff':
    st.header("📋 Bảng Lương Của Bạn")
    st.dataframe(df)