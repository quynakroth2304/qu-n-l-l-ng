# app.py
import streamlit as st
import pandas as pd
import os
import uuid
import time
from datetime import datetime, timedelta

import styles
import backend

# 1. INIT
st.set_page_config(page_title="Hệ Thống V47 Safe", layout="wide", page_icon="🛡️", initial_sidebar_state="expanded")
styles.load_css()
backend.init_db()

SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

# 2. SESSION
if 'user' not in st.session_state:
    token = st.query_params.get("session")
    auto_user = backend.verify_session_token(token) if token else None
    if auto_user:
        conn = backend.get_db_connection()
        ud = conn.execute('SELECT * FROM users WHERE username=?', (auto_user,)).fetchone()
        conn.close()
        if ud:
            st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]
    else: st.session_state.user = None

# ==========================================
# 3. FRAGMENTS
# ==========================================
@st.fragment(run_every=3)
def render_chat(room_id, my_name, my_role):
    conn = backend.get_db_connection()
    msgs = conn.execute("SELECT id, sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,)).fetchall()[::-1]
    conn.close()

    st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:13px; margin-bottom:15px;'>🏢 <b>{room_id}</b></div>", unsafe_allow_html=True)
    html = '<div class="chat-container">'
    last_sender = None
    
    for mid, sender, content, ts, mtype in msgs:
        is_me = (sender == my_name)
        align = "flex-end" if is_me else "flex-start"
        
        html += f'<div class="message-row { "msg-right" if is_me else "msg-left" }">'
        
        # Avatar
        if not is_me:
            if sender != last_sender: html += f'<img src="{backend.get_avatar_url(sender)}" class="chat-avatar">'
            else: html += '<div style="width:44px;"></div>'
        
        # Content
        body = ""
        if mtype == 'payment_request':
            st.markdown(html, unsafe_allow_html=True); html = ""
            with st.container():
                c1, c2 = st.columns([1, 15] if not is_me else [15, 1])
                with (c2 if not is_me else c1):
                    st.markdown(f"""<style>div[data-testid="stVerticalBlock"] > div {{ align-items: {align}; display: flex; flex-direction: column; }}</style>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="payment-card"><div style="font-weight:bold">💸 XÁC NHẬN</div><div>Quản lý <b>{sender}</b> đã chuyển:</div><div class="pay-amt">{int(float(content)):,.0f} VNĐ</div></div>""", unsafe_allow_html=True)
                    if my_role == 'staff' and not is_me:
                        mf = os.path.join(backend.STORAGE_DIR, st.session_state.user, "salary.xlsx"); df = backend.load_excel_safe(mf)
                        if len(df[df["Trạng thái"].str.lower()=="chờ xác nhận"]) > 0:
                            if st.button("✅ ĐÃ NHẬN TIỀN", key=f"p_{mid}", type="primary"):
                                df.loc[df["Trạng thái"].str.lower()=="chờ xác nhận", "Trạng thái"] = "đã nhận"; backend.save_excel_safe(df, mf)
                                conn=backend.get_db_connection(); conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (room_id, my_name, f"✅ Đã nhận đủ: {int(float(content)):,.0f}", datetime.now().strftime("%H:%M"), "text")); conn.commit(); conn.close(); st.rerun()
                        else: st.caption("✅ Hoàn tất")
                    else: st.caption("⏳ Chờ xác nhận...")
        elif mtype == 'image':
            if os.path.exists(content):
                import base64
                with open(content, "rb") as f: b64 = base64.b64encode(f.read()).decode()
                body = f'<img src="data:image/png;base64,{b64}" style="max-width:250px; border-radius:12px;">'
            else: body = "<i>⚠️ Ảnh lỗi</i>"
        elif mtype == 'call':
            link = content.split('|')[-1]
            body = f'<div style="background:#e0f2fe; padding:12px; border-radius:12px; border:1px solid #bae6fd;">📹 <b>{sender}</b> gọi... <br><a href="{link}" target="_blank" style="font-weight:bold;">Tham gia</a></div>'
        else:
            body = f'<div class="bubble bubble-{"right" if is_me else "left"}">{content}</div>'

        if body: html += f'<div>{body}<div style="font-size:10px; color:#94a3b8; text-align:{align}; margin-top:2px;">{ts}</div></div>'
        html += '</div>'
        last_sender = sender

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("""<script>var c=window.parent.document.querySelector('.chat-container');if(c)c.scrollTop=c.scrollHeight;</script>""", unsafe_allow_html=True)

# ==========================================
# 4. LOGIN SCREEN
# ==========================================
if st.session_state.user is None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center; color:#2563eb;'>🛡️ HỆ THỐNG V47</h1>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Đăng Nhập", "Đăng Ký", "Super Admin"])
        conn = backend.get_db_connection(); c = conn.cursor()
        
        with t1:
            u = st.text_input("User"); p = st.text_input("Password", type="password")
            if st.button("Login", type="primary", use_container_width=True):
                ud = c.execute('SELECT * FROM users WHERE username=? AND password=?', (u, p)).fetchone()
                if ud:
                    st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]
                    tk = backend.create_login_session(ud[0]); st.query_params["session"] = tk; st.rerun()
                else: st.error("Sai thông tin")
        
        with t2:
            c_a, c_b = st.columns(2)
            with c_a: ru = st.text_input("ID", key="r1"); rn = st.text_input("Tên", key="r2"); rp = st.text_input("SĐT", key="r3")
            with c_b: rpass = st.text_input("Pass", type="password", key="r4"); rr = st.radio("Role", ["Nhân viên", "Quản lý"])
            rwp = "ADMIN"; rk = ""
            if rr == "Nhân viên": rwp = st.text_input("Mã CN")
            elif rr == "Quản lý": rk = st.text_input("Key Admin", type="password")
            if st.button("Register", use_container_width=True):
                try:
                    if rr=="Nhân viên" and not c.execute("SELECT id FROM workplaces WHERE id=?", (rwp,)).fetchone(): st.error("Sai mã CN"); st.stop()
                    if rr=="Quản lý":
                        if not c.execute("SELECT key_code FROM license_keys WHERE key_code=? AND status='active'", (rk,)).fetchone(): st.error("Key lỗi"); st.stop()
                        c.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (rk,))
                    op = os.path.join(backend.STORAGE_DIR, ru); 
                    if os.path.exists(op): import shutil; shutil.rmtree(op)
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (ru, rpass, 'admin' if rr=="Quản lý" else 'staff', None, rn, rwp, rp, None, "2099-01-01"))
                    conn.commit(); st.success("OK! Login đi."); 
                except: st.error("User trùng")
        
        with t3:
            su = st.text_input("Super User"); sp = st.text_input("Super Pass", type="password")
            if st.button("Access", use_container_width=True):
                if su == SUPER_ADMIN_USER and sp == SUPER_ADMIN_PASS:
                    st.session_state.user="SUPER_ADMIN"; st.session_state.role="super_admin"; st.session_state.zalo="System"; st.session_state.wp_id="MASTER"; st.rerun()
                else: st.error("Sai!")
        conn.close(); st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 5. MAIN APP
# ==========================================
cu = st.session_state.user; cr = st.session_state.role; cz = st.session_state.zalo; cwp = st.session_state.wp_id
conn = backend.get_db_connection()

with st.sidebar:
    st.image(backend.get_avatar_url(cz), width=100); st.title(cz); st.caption(f"{cu} | {cr}")
    if cwp and cwp not in ["ADMIN", "MASTER"]: st.markdown(f"🏢 **{cwp}**")
    st.divider()
    if st.button("Đăng xuất", use_container_width=True):
        if "session" in st.query_params: conn.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],)); conn.commit()
        st.query_params.clear(); st.session_state.user=None; st.rerun()

# --- SUPER ADMIN (CÓ BACKUP) ---
if cr == 'super_admin':
    st.header("🔧 QUẢN TRỊ HỆ THỐNG")
    t1, t2, t3 = st.tabs(["🔑 Keys", "💾 Backup/Restore", "⚡ Reset"])
    with t1:
        if st.button("Sinh Key"): k=str(uuid.uuid4())[:8].upper(); conn.execute("INSERT INTO license_keys VALUES (?,365,'active')", (k,)); conn.commit(); st.success(k)
        st.dataframe(pd.read_sql("SELECT * FROM license_keys", conn))
    
    # [TÍNH NĂNG CỨU HỘ DỮ LIỆU]
    with t2:
        st.info("💡 Lưu ý: Hệ thống miễn phí sẽ xóa dữ liệu khi reset. Hãy tải Backup mỗi ngày!")
        # Nút tải xuống
        zip_buffer = backend.create_backup_zip()
        st.download_button("⬇️ TẢI DỮ LIỆU VỀ MÁY (Backup)", data=zip_buffer, file_name="system_backup.zip", mime="application/zip", type="primary")
        
        st.divider()
        # Nút nạp lại
        uploaded_file = st.file_uploader("⬆️ Nạp dữ liệu cũ (Restore)", type="zip")
        if uploaded_file:
            if st.button("Khôi phục ngay"):
                if backend.restore_backup_zip(uploaded_file): st.success("Đã khôi phục thành công! F5 lại trang."); time.sleep(2); st.rerun()
                else: st.error("File lỗi!")

    with t3:
        if st.button("💣 XÓA SẠCH (Hard Reset)"): backend.hard_reset(); st.cache_resource.clear(); st.success("Xong!"); st.stop()
    st.stop()

# --- APP TABS ---
tc, tw = st.tabs(["💬 Chat", "📊 Công Việc"])

with tc:
    aroom = cwp if cr != 'admin' else st.selectbox("Chi nhánh:", [r[0] for r in conn.execute("SELECT id FROM workplaces").fetchall()])
    if aroom:
        render_chat(aroom, cz, cr)
        c1, c2 = st.columns([6, 1])
        with c1: 
            if m := st.chat_input("Nhập tin nhắn..."): conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (aroom, cz, m, datetime.now().strftime("%H:%M"), "text")); conn.commit()
        with c2:
            with st.popover("➕", use_container_width=True):
                if st.button("Call"): l=f"https://meet.jit.si/{uuid.uuid4()}"; conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (aroom, cz, f"v|{l}", datetime.now().strftime("%H:%M"), "call")); conn.commit(); st.rerun()
                if u := st.file_uploader("", type=['jpg','png']): 
                    f=f"{uuid.uuid4()}.{u.name.split('.')[-1]}"; p=os.path.join(backend.UPLOAD_DIR, f)
                    with open(p, "wb") as x: x.write(u.getbuffer())
                    conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (aroom, cz, p, datetime.now().strftime("%H:%M"), "image")); conn.commit(); st.rerun()

with tw:
    if cr == 'admin':
        with st.expander("🏢 QUẢN LÝ"):
            if st.button("Tạo CN Mới"): 
                nid = st.text_input("Mã CN"); nnm = st.text_input("Tên")
                if nid: 
                    try: conn.execute("INSERT INTO workplaces VALUES (?,?,?)", (nid, nnm, cu)); conn.commit(); st.success("OK")
                    except: st.error("Trùng")
        
        sl = conn.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        if sl:
            sel = st.selectbox("NV:", [f"{s[1]} ({s[0]})" for s in sl]); tid = sel.split('(')[1].replace(')', '')
            tf = os.path.join(backend.STORAGE_DIR, tid, "salary.xlsx"); df = backend.load_excel_safe(tf)
            
            pcount = len(df[df["Xác nhận đến"] == False]); debt = pd.to_numeric(df[~df["Trạng thái"].str.contains("đã nhận")]["Tổng lương"], errors='coerce').sum()
            
            c1, c2, c3 = st.columns(3); c1.metric("Nợ", f"{debt:,.0f}"); c2.metric("Chờ duyệt", pcount)
            with c3:
                if pcount > 0 and st.button("✅ Duyệt chấm công", type="primary"): df.loc[df["Xác nhận đến"]==False, "Xác nhận đến"]=True; backend.save_excel_safe(df, tf); st.rerun()
                if debt > 0 and st.button("💸 Báo chuyển khoản"):
                    df.loc[~df["Trạng thái"].str.contains("đã nhận"), "Trạng thái"] = "chờ xác nhận"; backend.save_excel_safe(df, tf)
                    twp = [s[2] for s in sl if s[0]==tid][0]
                    conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (twp, cz, str(debt), datetime.now().strftime("%H:%M"), "payment_request")); conn.commit(); st.success("Đã báo!"); st.rerun()
            
            with st.expander("Thêm ca"):
                d=st.date_input("Ngày"); v=st.text_input("VT","Tại quán"); t1=st.time_input("In"); t2=st.time_input("Out"); r=st.number_input("Lương",20000)
                if st.button("Lưu"):
                    dt1=datetime.combine(d,t1); dt2=datetime.combine(d,t2); 
                    if dt2<dt1: dt2+=timedelta(days=1)
                    h=(dt2-dt1).seconds/3600; new=pd.DataFrame([{"Ngày":d.strftime("%Y-%m-%d"),"Vị trí":v,"Giờ vào":t1.strftime("%H:%M"),"Giờ ra":t2.strftime("%H:%M"),"Tổng lương":h*r,"Trạng thái":"chưa nhận","Xác nhận đến":True}])
                    backend.save_excel_safe(pd.concat([df,new],ignore_index=True), tf); st.success("OK"); st.rerun()
            st.dataframe(df)

    elif cr == 'staff':
        mf = os.path.join(backend.STORAGE_DIR, cu, "salary.xlsx"); dfm = backend.load_excel_safe(mf)
        debt = pd.to_numeric(dfm[~dfm["Trạng thái"].str.contains("đã nhận")]["Tổng lương"], errors='coerce').sum()
        
        st.metric("Quán nợ:", f"{debt:,.0f}")
        if debt > 0 and st.button("🔔 Nhắc quản lý"): conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (cwp, cz, f"Check lương: {debt:,.0f}", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.toast("Sent!")
        
        with st.expander("Báo cáo ca"):
            d=st.date_input("Ngày"); v=st.text_input("VT",cwp); t1=st.time_input("In"); t2=st.time_input("Out"); r=st.number_input("Lương",20000)
            if st.button("Gửi", type="primary"):
                dt1=datetime.combine(d,t1); dt2=datetime.combine(d,t2); 
                if dt2<dt1: dt2+=timedelta(days=1)
                h=(dt2-dt1).seconds/3600; new=pd.DataFrame([{"Ngày":d.strftime("%Y-%m-%d"),"Vị trí":v,"Giờ vào":t1.strftime("%H:%M"),"Giờ ra":t2.strftime("%H:%M"),"Tổng lương":h*r,"Trạng thái":"chưa nhận","Xác nhận đến":False}])
                backend.save_excel_safe(pd.concat([dfm,new],ignore_index=True), mf); st.success("Lưu!"); st.rerun()
        st.dataframe(dfm)

conn.close()