# app.py
import streamlit as st
import pandas as pd
import os
import uuid
import time
from datetime import datetime, timedelta

# Import modules
import styles
import backend

# 1. Cấu hình & Khởi tạo
st.set_page_config(
    page_title="Hệ Thống Quản Lý V46", 
    layout="wide", 
    page_icon="✨", 
    initial_sidebar_state="expanded"
)
styles.load_css() # Load giao diện mới
backend.init_db()

SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

# 2. Session Management
if 'user' not in st.session_state:
    token = st.query_params.get("session")
    auto_user = backend.verify_session_token(token) if token else None
    
    if auto_user:
        conn = backend.get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE username=?', (auto_user,)).fetchone()
        conn.close()
        if user_data:
            st.session_state.user = user_data[0]
            st.session_state.role = user_data[2]
            st.session_state.zalo = user_data[4]
            st.session_state.wp_id = user_data[5]
            st.session_state.expiry = user_data[8]
    else:
        st.session_state.user = None

# ==========================================
# 3. UI FRAGMENTS (Chat & Dashboard)
# ==========================================
@st.fragment(run_every=3)
def render_chat(room_id, my_name, my_role):
    conn = backend.get_db_connection()
    msgs = conn.execute("SELECT id, sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,)).fetchall()[::-1]
    conn.close()

    st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:13px; font-weight:500; margin-bottom:20px; letter-spacing:0.5px;'>🏢 Phòng chat: <b>{room_id}</b></div>", unsafe_allow_html=True)
    
    last_sender = None
    html_content = '<div class="chat-container">'
    
    for mid, sender, content, ts, mtype in msgs:
        is_me = (sender == my_name)
        align = "flex-end" if is_me else "flex-start"
        
        # Bắt đầu hàng tin nhắn
        html_content += f'<div class="message-row { "message-right" if is_me else "message-left" }">'

        # Avatar người khác
        if not is_me and sender != last_sender:
             html_content += f'<img src="{backend.get_avatar_url(sender)}" class="chat-avatar" title="{sender}">'
        elif not is_me:
             html_content += '<div style="width:52px;"></div>' # Placeholder cho avatar

        # Nội dung tin nhắn
        msg_body = ""
        if mtype == 'payment_request':
            # Render Payment Bubble bằng st.markdown để dùng được nút bấm của Streamlit
            # (Phần này hơi tricky khi kết hợp HTML string và Streamlit component)
            # Giải pháp: Đóng HTML string lại, render nút, rồi mở lại.
            st.markdown(html_content, unsafe_allow_html=True) # Render phần trước đó
            html_content = "" # Reset buffer

            # Render Payment UI bằng Streamlit thuần
            with st.container():
                 c1, c2 = st.columns([1, 15] if not is_me else [15, 1])
                 target_col = c2 if not is_me else c1
                 with target_col:
                    st.markdown(f"""<style>div[data-testid="stVerticalBlock"] > div {{ align-items: {align}; display: flex; flex-direction: column; }}</style>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="payment-bubble"><div class="payment-header">💸 XÁC NHẬN THANH TOÁN</div><div>Quản lý <b>{sender}</b> đã chuyển khoản:</div><div class="payment-amount">{int(float(content)):,.0f} VNĐ</div></div>""", unsafe_allow_html=True)
                    
                    if my_role == 'staff' and not is_me:
                        mf = os.path.join(backend.STORAGE_DIR, st.session_state.user, "salary.xlsx"); df = backend.load_excel_safe(mf)
                        if len(df[df["Trạng thái"].str.lower()=="chờ xác nhận"]) > 0:
                            # Sử dụng nút primary cho hành động quan trọng
                            if st.button("✅ XÁC NHẬN ĐÃ NHẬN TIỀN", key=f"p_{mid}", type="primary", use_container_width=True):
                                df.loc[df["Trạng thái"].str.lower()=="chờ xác nhận", "Trạng thái"] = "đã nhận"; backend.save_excel_safe(df, mf)
                                conn = backend.get_db_connection()
                                conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (room_id, my_name, f"✅ Đã nhận đủ: {int(float(content)):,.0f} VNĐ", datetime.now().strftime("%H:%M"), "text")); conn.commit(); conn.close()
                                st.rerun()
                        else: st.caption("✅ Giao dịch đã hoàn tất")
                    else: st.caption(f"⏳ {ts} - Đang chờ xác nhận...")

        elif mtype == 'image': 
            if os.path.exists(content): 
                import base64
                with open(content, "rb") as f: img_b64 = base64.b64encode(f.read()).decode()
                msg_body = f'<img src="data:image/png;base64,{img_b64}" style="max-width:250px; border-radius:12px; box-shadow: var(--shadow-sm);">'
            else: msg_body = "<i>⚠️ Ảnh đã xóa</i>"
        elif mtype == 'call':
            link = content.split('|')[-1]
            icon = "📹" if "video" in content else "📞"
            msg_body = f'<div style="background:#e0f2fe; padding:12px; border-radius:12px; border:1px solid #bae6fd; display:flex; align-items:center; gap:10px;"><span style="font-size:24px">{icon}</span><div><div style="font-weight:bold;">{sender} đang gọi...</div><a href="{link}" target="_blank" style="color:#0284c7; text-decoration:none; font-weight:600;">Tham gia ngay →</a></div></div>'
        else: # Text
            msg_body = f'<div class="bubble-{"right" if is_me else "left"}">{content}</div>'

        if mtype != 'payment_request':
            html_content += f'<div>{msg_body}<div class="chat-timestamp" style="text-align: {align};">{ts}</div></div>'
        
        html_content += '</div>' # End message-row
        last_sender = sender

    html_content += '</div>' # End chat-container
    st.markdown(html_content, unsafe_allow_html=True)
    
    # Auto-scroll script
    st.markdown("""<script>var chatDiv = window.parent.document.querySelector('.chat-container'); if (chatDiv) { chatDiv.scrollTop = chatDiv.scrollHeight; }</script>""", unsafe_allow_html=True)

# ==========================================
# 4. MÀN HÌNH LOGIN (GIAO DIỆN MỚI)
# ==========================================
if st.session_state.user is None:
    # Sử dụng columns để căn giữa và tạo khung login card
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        # Bọc nội dung vào một thẻ div có class login-card
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center; color:var(--primary-color); margin-bottom: 10px;'>✨ HỆ THỐNG V46</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:var(--text-gray); margin-bottom: 30px;'>Quản lý nhân sự & Tiền lương chuyên nghiệp</p>", unsafe_allow_html=True)
        
        t1, t2, t3 = st.tabs(["Đăng Nhập", "Đăng Ký", "Super Admin"])
        
        conn = backend.get_db_connection(); c = conn.cursor()
        
        with t1:
            st.markdown("<br>", unsafe_allow_html=True) # Khoảng cách
            u = st.text_input("Tên đăng nhập", placeholder="Nhập username..."); p = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu...")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Đăng nhập ngay", type="primary", use_container_width=True):
                ud = c.execute('SELECT * FROM users WHERE username=? AND password=?', (u, p)).fetchone()
                if ud:
                    st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]
                    tk = backend.create_login_session(ud[0]); st.query_params["session"] = tk; st.rerun()
                else: st.error("Thông tin đăng nhập không đúng.")
        
        with t2:
            st.markdown("<br>", unsafe_allow_html=True)
            ca, cb = st.columns(2)
            with ca: ru = st.text_input("User ID (Viết liền)", key="r1"); rn = st.text_input("Tên hiển thị (Zalo)", key="r2"); rp = st.text_input("Số điện thoại", key="r3")
            with cb: rpass = st.text_input("Mật khẩu", type="password", key="r4"); rr = st.radio("Vai trò", ["Nhân viên", "Quản lý"], horizontal=True)
            rwp = "ADMIN"; rk = ""
            if rr == "Nhân viên": rwp = st.text_input("Mã Chi Nhánh (Do quản lý cấp)")
            elif rr == "Quản lý": rk = st.text_input("Key Kích Hoạt (Từ Admin)", type="password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Tạo tài khoản mới", use_container_width=True):
                try:
                    if rr=="Nhân viên" and not c.execute("SELECT id FROM workplaces WHERE id=?", (rwp,)).fetchone(): st.error("Mã Chi Nhánh không tồn tại!"); st.stop()
                    if rr=="Quản lý":
                        if not c.execute("SELECT key_code FROM license_keys WHERE key_code=? AND status='active'", (rk,)).fetchone(): st.error("Key không hợp lệ hoặc hết hạn!"); st.stop()
                        c.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (rk,))
                    
                    op = os.path.join(backend.STORAGE_DIR, ru); 
                    if os.path.exists(op): shutil.rmtree(op)
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (ru, rpass, 'admin' if rr=="Quản lý" else 'staff', None, rn, rwp, rp, None, "2099-01-01"))
                    conn.commit(); st.success("Đăng ký thành công! Hãy đăng nhập."); 
                except sqlite3.IntegrityError: st.error("Tên đăng nhập đã tồn tại.")
        
        with t3:
            st.markdown("<br>", unsafe_allow_html=True)
            su = st.text_input("Super User"); sp = st.text_input("Super Password", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Truy cập hệ thống gốc", use_container_width=True):
                if su == SUPER_ADMIN_USER and sp == SUPER_ADMIN_PASS:
                    st.session_state.user="SUPER_ADMIN"; st.session_state.role="super_admin"; st.session_state.zalo="System Administrator"; st.session_state.wp_id="MASTER"; st.rerun()
                else: st.error("Thông tin không chính xác!")
        
        conn.close()
        st.markdown('</div>', unsafe_allow_html=True) # Đóng login-card
    st.stop()

# ==========================================
# 5. MAIN APP (SAU KHI ĐĂNG NHẬP)
# ==========================================
cu = st.session_state.user; cr = st.session_state.role; cz = st.session_state.zalo; cwp = st.session_state.wp_id
conn = backend.get_db_connection()

# --- SIDEBAR ---
with st.sidebar:
    st.image(backend.get_avatar_url(cz), width=110)
    st.markdown(f"<h2 style='margin-top:10px; margin-bottom:5px;'>{cz}</h2>", unsafe_allow_html=True)
    
    role_display = "Quản Lý" if cr == 'admin' else ("Nhân Viên" if cr == 'staff' else "Super Admin")
    st.markdown(f"<div style='color:var(--text-gray); font-weight:500;'>{role_display} | ID: {cu}</div>", unsafe_allow_html=True)
    
    if cwp and cwp not in ["ADMIN", "MASTER"]:
        st.markdown(f"<div style='
            margin-top:15px; 
            padding:8px 12px; 
            background:#f1f5f9; 
            border-radius:8px; 
            font-size:13px; 
            color:#475569; 
            display:flex; 
            align-items:center; 
            gap:8px;'>
            🏢 Chi nhánh: <b>{cwp}</b>
        </div>", unsafe_allow_html=True)

    st.divider()
    # Nút đăng xuất màu đỏ nhẹ
    if st.button("🚪 Đăng xuất", use_container_width=True):
        if "session" in st.query_params: conn.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],)); conn.commit()
        st.query_params.clear(); st.session_state.user=None; st.rerun()

# --- SUPER ADMIN ---
if cr == 'super_admin':
    st.header("🔧 SUPER ADMIN CONTROL PANEL"); t1, t2 = st.tabs(["Quản Lý Key", "Hệ Thống"])
    with t1:
        kt = st.selectbox("Loại Key", ["30 Ngày", "365 Ngày", "Vĩnh viễn"]); 
        if st.button("Sinh Key Mới", type="primary"): 
            k = str(uuid.uuid4())[:8].upper(); d = 36500 if kt == "Vĩnh viễn" else (365 if kt == "365 Ngày" else 30)
            conn.execute("INSERT INTO license_keys VALUES (?,?,?)", (k, d, "active")); conn.commit(); st.success(f"Key đã tạo: {k}")
        st.dataframe(pd.read_sql("SELECT * FROM license_keys", conn), use_container_width=True)
    with t2:
        st.error("Vùng nguy hiểm!")
        if st.button("💣 RESET TOÀN BỘ DỮ LIỆU HỆ THỐNG", type="primary"): backend.hard_reset(); st.cache_resource.clear(); st.success("Hệ thống đã được reset!"); st.stop()
    st.stop()

# --- APP TABS ---
tc, tw = st.tabs(["💬 Trung Tâm Liên Lạc", "📊 Quản Lý & Công Việc"])

with tc:
    # Chọn phòng chat
    if cr == 'admin':
        workplaces = [r[0] for r in conn.execute("SELECT id FROM workplaces").fetchall()]
        if workplaces:
            aroom = st.selectbox("Chọn Chi Nhánh làm việc:", workplaces)
        else:
            st.info("Chưa có chi nhánh nào. Vui lòng tạo chi nhánh bên tab 'Quản Lý'.")
            aroom = None
    else:
        aroom = cwp

    if aroom:
        render_chat(aroom, cz, cr)
        
        # Input area
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([8, 1, 1])
        with c1: 
            if m := st.chat_input("Nhập tin nhắn..."): 
                conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (aroom, cz, m, datetime.now().strftime("%H:%M"), "text")); conn.commit()
        with c2:
            with st.popover("📹", use_container_width=True):
                if st.button("Tạo cuộc gọi Video", use_container_width=True): 
                    lk = f"https://meet.jit.si/v_{uuid.uuid4()}"
                    conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (aroom, cz, f"v|{lk}", datetime.now().strftime("%H:%M"), "call")); conn.commit(); st.rerun()
        with c3:
            with st.popover("🖼️", use_container_width=True):
                u = st.file_uploader("Chọn ảnh", type=['jpg','png'], label_visibility="collapsed")
                if u and st.button("Gửi Ảnh", type="primary", use_container_width=True): 
                    f=f"{uuid.uuid4()}.{u.name.split('.')[-1]}"; p=os.path.join(backend.UPLOAD_DIR, f)
                    with open(p, "wb") as x: x.write(u.getbuffer())
                    conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (aroom, cz, p, datetime.now().strftime("%H:%M"), "image")); conn.commit(); st.rerun()

with tw:
    if cr == 'admin':
        with st.expander("🏢 QUẢN LÝ CHI NHÁNH", expanded=True):
            c_cr, c_li = st.tabs(["Tạo Mới", "Danh Sách"])
            with c_cr:
                c1, c2 = st.columns(2)
                nid = c1.text_input("Mã Chi Nhánh (VD: CN01)"); nnm = c2.text_input("Tên Hiển Thị (VD: Cafe Trung Tâm)")
                if st.button("Tạo Chi Nhánh", type="primary"): 
                    if nid and nnm:
                        try: conn.execute("INSERT INTO workplaces VALUES (?,?,?)", (nid.upper(), nnm, cu)); conn.commit(); st.success("Đã tạo thành công!")
                        except: st.error("Mã chi nhánh đã tồn tại.")
                    else: st.warning("Vui lòng điền đủ thông tin.")
            with c_li:
                st.dataframe(pd.read_sql(f"SELECT id as 'Mã CN', name as 'Tên CN' FROM workplaces WHERE created_by='{cu}'", conn), use_container_width=True)
        
        st.divider()
        sl = conn.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        if sl:
            st.subheader("Danh Sách Nhân Viên")
            sel = st.selectbox("Chọn nhân viên để quản lý:", [f"{s[1]} ({s[0]}) - CN: {s[2]}" for s in sl])
            tid = sel.split('(')[1].split(')')[0]
            tf = os.path.join(backend.STORAGE_DIR, tid, "salary.xlsx"); df = backend.load_excel_safe(tf)
            
            pcount = len(df[df["Xác nhận đến"] == False])
            debt = pd.to_numeric(df[~df["Trạng thái"].str.contains("đã nhận")]["Tổng lương"], errors='coerce').sum()
            
            # Metrics with custom styling
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"""<div class="metric-card"><div class="metric-value">{debt:,.0f}</div><div class="metric-label">Tổng Quỹ Lương Nợ</div></div>""", unsafe_allow_html=True)
            c2.markdown(f"""<div class="metric-card"><div class="metric-value" style="color: {'var(--danger-color)' if pcount > 0 else 'var(--success-color)'}">{pcount}</div><div class="metric-label">Ca Chờ Duyệt</div></div>""", unsafe_allow_html=True)
            
            with c3:
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True) # Spacer
                if pcount > 0:
                    if st.button("✅ DUYỆT TẤT CẢ CHẤM CÔNG", type="primary", use_container_width=True):
                        df.loc[df["Xác nhận đến"]==False, "Xác nhận đến"]=True; backend.save_excel_safe(df, tf); st.success("Đã duyệt!"); time.sleep(0.5); st.rerun()
                
                if debt > 0:
                    if st.button("💸 BÁO ĐÃ CHUYỂN KHOẢN LƯƠNG", use_container_width=True):
                        df.loc[~df["Trạng thái"].str.contains("đã nhận"), "Trạng thái"] = "chờ xác nhận"; backend.save_excel_safe(df, tf)
                        twp = [s[2] for s in sl if s[0]==tid][0]
                        conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (twp, cz, str(debt), datetime.now().strftime("%H:%M"), "payment_request")); conn.commit(); st.success("Đã gửi yêu cầu xác nhận!"); st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("➕ Thêm Ca Làm Việc Thủ Công"):
                with st.form("aa"):
                    c_d, c_v = st.columns(2); d=c_d.date_input("Ngày"); v=c_v.text_input("Vị trí", "Tại quán")
                    c_t1, c_t2, c_r = st.columns(3); t1=c_t1.time_input("Giờ vào"); t2=c_t2.time_input("Giờ ra"); r=c_r.number_input("Lương/giờ", value=25000, step=1000)
                    if st.form_submit_button("Lưu Ca Làm Việc", type="primary", use_container_width=True):
                        dt1=datetime.combine(d,t1); dt2=datetime.combine(d,t2); 
                        if dt2<dt1: dt2+=timedelta(days=1)
                        h=(dt2-dt1).seconds/3600; new=pd.DataFrame([{"Ngày":d.strftime("%Y-%m-%d"),"Vị trí":v,"Giờ vào":t1.strftime("%H:%M"),"Giờ ra":t2.strftime("%H:%M"),"Tổng lương":h*r,"Trạng thái":"chưa nhận","Xác nhận đến":True}])
                        backend.save_excel_safe(pd.concat([df,new],ignore_index=True), tf); st.success("Đã thêm thành công!"); st.rerun()
            
            st.markdown("### Lịch Sử Làm Việc & Lương")
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("Chưa có nhân viên nào trong hệ thống.")

    elif cr == 'staff':
        mf = os.path.join(backend.STORAGE_DIR, cu, "salary.xlsx"); dfm = backend.load_excel_safe(mf)
        debt = pd.to_numeric(dfm[~dfm["Trạng thái"].str.contains("đã nhận")]["Tổng lương"], errors='coerce').sum()
        pcount = len(dfm[dfm["Xác nhận đến"] == False])

        c1, c2 = st.columns(2)
        c1.markdown(f"""<div class="metric-card"><div class="metric-value">{debt:,.0f}</div><div class="metric-label">Lương Chưa Nhận</div></div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class="metric-card"><div class="metric-value" style="color: {'var(--text-gray)' if pcount == 0 else 'var(--primary-color)'}">{pcount}</div><div class="metric-label">Ca Đang Chờ Duyệt</div></div>""", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if debt > 0:
             if st.button("🔔 Gửi tin nhắn nhắc Quản Lý về lương", use_container_width=True):
                 conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (cwp, cz, f"📣 Anh/Chị ơi, check giúp em khoản lương: {debt:,.0f} VNĐ với ạ!", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.toast("Đã gửi tin nhắn nhắc nhở!", icon="✅")

        st.divider()
        with st.expander("➕ Báo Cáo Ca Làm Việc Mới", expanded=True):
            with st.form("sa"):
                c_d, c_v = st.columns(2); d=c_d.date_input("Ngày"); v=c_v.text_input("Vị trí", cwp)
                c_t1, c_t2, c_r = st.columns(3); t1=c_t1.time_input("Giờ vào"); t2=c_t2.time_input("Giờ ra"); r=c_r.number_input("Lương/giờ", value=25000, step=1000)
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Gửi Báo Cáo", type="primary", use_container_width=True):
                    dt1=datetime.combine(d,t1); dt2=datetime.combine(d,t2); 
                    if dt2<dt1: dt2+=timedelta(days=1)
                    h=(dt2-dt1).seconds/3600; new=pd.DataFrame([{"Ngày":d.strftime("%Y-%m-%d"),"Vị trí":v,"Giờ vào":t1.strftime("%H:%M"),"Giờ ra":t2.strftime("%H:%M"),"Tổng lương":h*r,"Trạng thái":"chưa nhận","Xác nhận đến":False}])
                    backend.save_excel_safe(pd.concat([dfm,new],ignore_index=True), mf); st.success("Đã gửi báo cáo! Vui lòng chờ duyệt."); st.rerun()
        
        st.markdown("### Bảng Lương Của Bạn")
        st.dataframe(dfm, use_container_width=True, height=400)

conn.close()