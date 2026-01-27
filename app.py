import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from PIL import Image

# --- CẤU HÌNH ---
DB_FILE = "system_users_v3.db" # Đổi tên DB để tạo cấu trúc mới
STORAGE = "user_files"
if not os.path.exists(STORAGE): os.makedirs(STORAGE)

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# 1. Bảng người dùng (Thêm cột workplace_id)
c.execute('''CREATE TABLE IF NOT EXISTS users
             (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
              qr_path TEXT, zalo_name TEXT, workplace_id TEXT)''')

# 2. Bảng nơi làm việc (Lưu các mã ID do admin tạo)
c.execute('''CREATE TABLE IF NOT EXISTS workplaces
             (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''')
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

st.set_page_config(page_title="Hệ Thống Quản Lý V6", layout="wide")

# --- PHẦN 1: ĐĂNG NHẬP / ĐĂNG KÝ ---
if 'user' not in st.session_state:
    st.title("🛡️ Hệ Thống Quản Lý Đa Chi Nhánh (V6)")
    
    t_log, t_reg, t_res = st.tabs(["Đăng nhập", "Đăng ký", "Tải file cứu hộ"])
    
    with t_res:
        up = st.file_uploader("Tải file Excel cũ", type="xlsx")
        if up: st.session_state.temp_file = up

    with t_reg:
        st.caption("📝 Điền thông tin bên dưới")
        c1, c2 = st.columns(2)
        with c1: 
            u_r = st.text_input("Tên đăng nhập (ID)", key="reg_user")
            z_r = st.text_input("Tên Zalo (Hiển thị)", key="reg_zalo")
        with c2: 
            p_r = st.text_input("Mật khẩu", type='password', key="reg_pass")
            
        r_r = st.radio("Bạn đăng ký với vai trò gì?", ["Nhân viên", "Quản lý"], horizontal=True, key="reg_role")
        
        # LOGIC RIÊNG CHO TỪNG VAI TRÒ
        wp_id_input = ""
        if r_r == "Nhân viên":
            st.info("ℹ️ Bạn cần nhập Mã nơi làm việc do Quản lý cung cấp.")
            wp_id_input = st.text_input("Nhập Mã ID Nơi Làm Việc (VD: CAFE_01)", key="reg_wp").strip()
        else:
            st.info("ℹ️ Sau khi tạo tài khoản Quản lý, bạn sẽ được vào tạo Mã Nơi Làm Việc.")

        if st.button("Tạo tài khoản", key="btn_reg"):
            if u_r and p_r and z_r:
                try:
                    role_code = 'admin' if r_r == "Quản lý" else 'staff'
                    
                    # KIỂM TRA MÃ NƠI LÀM VIỆC (NẾU LÀ NHÂN VIÊN)
                    final_wp_id = "ADMIN" # Admin mặc định không cần mã
                    if role_code == 'staff':
                        if not wp_id_input:
                            st.error("Vui lòng nhập Mã nơi làm việc!")
                            st.stop()
                        
                        # Check trong DB xem mã có tồn tại không
                        c.execute("SELECT id FROM workplaces WHERE id=?", (wp_id_input,))
                        if not c.fetchone():
                            st.error(f"❌ Mã '{wp_id_input}' không tồn tại! Hãy hỏi lại Quản lý.")
                            st.stop()
                        final_wp_id = wp_id_input

                    # Tạo tài khoản
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?,?)', (u_r, p_r, role_code, None, z_r, final_wp_id))
                    conn.commit()
                    st.success("✅ Đăng ký thành công! Hãy chuyển qua tab Đăng nhập.")
                except sqlite3.IntegrityError:
                    st.error("Tên đăng nhập này đã tồn tại.")
            else: st.warning("Nhập thiếu thông tin!")

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
    # --- 1. QUẢN LÝ MÃ NƠI LÀM VIỆC (TÍNH NĂNG MỚI) ---
    with st.expander("🏢 QUẢN LÝ MÃ NƠI LÀM VIỆC (Tạo mã cho nhân viên)", expanded=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.write(" **Tạo Mã Mới**")
            new_wp_id = st.text_input("Mã ID (VD: CAFE_01)").upper().strip()
            new_wp_name = st.text_input("Tên hiển thị (VD: Cafe Quận 1)")
            if st.button("Lưu Mã Mới"):
                if new_wp_id and new_wp_name:
                    try:
                        c.execute("INSERT INTO workplaces VALUES (?,?,?)", (new_wp_id, new_wp_name, user))
                        conn.commit()
                        st.success(f"Đã tạo: {new_wp_id}")
                        st.rerun()
                    except: st.error("Mã ID này đã tồn tại!")
                else: st.warning("Nhập đủ thông tin!")
        
        with c2:
            st.write("📋 **Danh sách Mã đang hoạt động**")
            c.execute("SELECT id, name FROM workplaces")
            wps = c.fetchall()
            if wps:
                st.dataframe(pd.DataFrame(wps, columns=["Mã ID (Cấp cho NV)", "Tên Chi Nhánh"]), use_container_width=True)
            else:
                st.info("Chưa có mã nào. Hãy tạo mã đầu tiên để nhân viên đăng ký!")

    st.divider()
    st.header("🔔 Trung Tâm Điều Hành")

    # === KHU VỰC TÍNH TOÁN TỔNG HỢP ===
    now = datetime.now()
    alerts = []
    total_system_debt = 0 
    debt_details_list = [] 
    
    try:
        # Lấy nhân viên kèm theo nơi làm việc
        c.execute("SELECT username, zalo_name, workplace_id FROM users WHERE role='staff'")
        staffs = c.fetchall()
    except: staffs = []
    
    for s_id, s_name, s_wp in staffs:
        p = os.path.join(STORAGE, s_id, "salary.xlsx")
        if os.path.exists(p):
            try:
                df_s = pd.read_excel(p)
                c_n = find_col(df_s, ["ngày"])
                c_v = find_col(df_s, ["vào", "start"])
                c_tt = find_col(df_s, ["trạng thái", "nhận"])
                c_tl = find_col(df_s, ["tổng", "lương"])
                
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
                                alerts.append(f"⚠️ **{status} ({int(diff)}p)**: {s_name} ({s_wp}) - {time_str}")
                        except: pass
                
                if c_tt and c_tl:
                    debt_rows = df_s[df_s[c_tt].astype(str).str.lower().str.contains('chưa', na=False)]
                    s_debt = pd.to_numeric(debt_rows[c_tl], errors='coerce').sum()
                    if s_debt > 0:
                        total_system_debt += s_debt
                        debt_details_list.append({
                            "Tên nhân viên": s_name,
                            "Nơi làm (ID)": s_wp, # Hiển thị ID nơi làm
                            "Số tiền nợ (VNĐ)": s_debt,
                            "ID": s_id
                        })
            except: pass

    st.subheader("💰 Bảng Kê Khai Công Nợ")
    st.metric(label="TỔNG SỐ TIỀN CẦN THANH TOÁN", value=f"{total_system_debt:,.0f} VNĐ")
    
    if debt_details_list:
        st.write("🔻 **Chi tiết nợ từng nhân viên:**")
        st.dataframe(pd.DataFrame(debt_details_list).style.format({"Số tiền nợ (VNĐ)": "{:,.0f}"}), use_container_width=True)
    else: st.success("Không nợ lương.")

    if alerts:
        with st.expander("📲 Cần gọi nhắc nhở", expanded=True):
            for a in alerts: st.write(a)

    st.divider()

    # 2. ĐIỂM DANH
    st.subheader("📅 Điểm Danh & Chi Phí Hôm Nay")
    
    # LỌC THEO NƠI LÀM VIỆC
    c.execute("SELECT id FROM workplaces")
    all_wps = [x[0] for x in c.fetchall()]
    c_filter1, c_filter2 = st.columns(2)
    with c_filter1: view_date = st.date_input("Chọn ngày:", datetime.now())
    with c_filter2: filter_wp = st.selectbox("Lọc theo Chi nhánh:", ["Tất cả"] + all_wps)

    daily_data = []
    total_day_cost = 0 
    
    # Lọc nhân viên theo chi nhánh đã chọn
    target_staffs = staffs if filter_wp == "Tất cả" else [s for s in staffs if s[2] == filter_wp]

    for s_id, s_name, s_wp in target_staffs:
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
                        hours = 0
                        salary = 0
                        try:
                            if c_vao and c_ra:
                                t1 = datetime.strptime(str(row[c_vao]), "%H:%M")
                                t2 = datetime.strptime(str(row[c_ra]), "%H:%M")
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
        st.info(f"💵 Chi phí ngày {view_date.strftime('%d/%m')}: **{total_day_cost:,.0f} VNĐ**")
        res_df = pd.DataFrame(daily_data)
        edited_df = st.data_editor(
            res_df[["Tên", "Chi nhánh", "Giờ vào", "Giờ ra", "Số giờ", "Lương (VNĐ)", "Đã đến"]],
            column_config={"Đã đến": st.column_config.CheckboxColumn("Xác nhận"), "Số giờ": st.column_config.NumberColumn(format="%.2f h")},
            disabled=["Tên", "Chi nhánh", "Giờ vào", "Giờ ra", "Số giờ", "Lương (VNĐ)"], hide_index=True,
        )
        if st.button("💾 Lưu xác nhận"):
            for i, row in edited_df.iterrows():
                original = daily_data[i]
                if row["Đã đến"] != original["Đã đến"]:
                    u_p = os.path.join(STORAGE, original["ID"], "salary.xlsx")
                    u_df = pd.read_excel(u_p)
                    c_chk = find_col(u_df, ["xác nhận", "checkin"])
                    u_df.at[original["File_Index"], c_chk] = True
                    u_df.to_excel(u_p, index=False)
            st.success("Đã cập nhật!"); st.rerun()
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
    i_vt = st.text_input("Vị trí chi tiết (VD: Bàn 1)")
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
        st.success("Đã thêm ca!"); st.rerun()

if role == 'staff':
    st.header("📋 Bảng Lương Của Bạn")
    st.dataframe(df)