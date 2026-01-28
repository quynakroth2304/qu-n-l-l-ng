# app.py
import streamlit as st
import pandas as pd
import os
import uuid
import time
from datetime import datetime, timedelta

# Import các module riêng đã tách
import styles
import backend

# 1. Cấu hình
st.set_page_config(page_title="Hệ Thống V45 Modular", layout="wide", page_icon="💎", initial_sidebar_state="expanded")
styles.load_css() # Load giao diện từ styles.py
backend.init_db() # Khởi tạo DB từ backend.py

SUPER_ADMIN_USER = "admin_vip"
SUPER_ADMIN_PASS = "vip888"

# 2. Khởi tạo Session
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
# 3. CÁC HÀM GIAO DIỆN (UI FRAGMENTS)
# ==========================================
@st.fragment(run_every=3)
def render_chat(room_id, my_name, my_role):
    conn = backend.get_db_connection()
    msgs = conn.execute("SELECT id, sender, content, timestamp, msg_type FROM messages WHERE workplace_id=? ORDER BY id DESC LIMIT 50", (room_id,)).fetchall()[::-1]
    
    st.markdown(f"<div style='text-align:center; color:#999; font-size:12px; margin-bottom:10px;'>🏢 {room_id}</div>", unsafe_allow_html=True)
    
    last_sender = None
    for mid, sender, content, ts, mtype in msgs:
        is_me = (sender == my_name)
        align = "flex-end" if is_me else "flex-start"
        
        with st.container():
            c1, c2 = st.columns([1, 15] if not is_me else [15, 1])
            if not is_me:
                with c1: 
                    if sender != last_sender: st.image(backend.get_avatar_url(sender), width=35)
            
            with (c2 if not is_me else c1):
                st.markdown(f"""<style>div[data-testid="stVerticalBlock"] > div {{ align-items: {align}; display: flex; flex-direction: column; }}</style>""", unsafe_allow_html=True)
                
                if mtype == 'payment_request':
                    st.markdown(f"""<div class="payment-bubble" style="margin-bottom:5px; align-self:{align};"><div class="payment-header">💸 XÁC NHẬN</div><div>Quản lý {sender} đã chuyển:</div><div class="payment-amount">{int(float(content)):,.0f} VNĐ</div></div>""", unsafe_allow_html=True)
                    if my_role == 'staff' and not is_me:
                        mf = os.path.join(backend.STORAGE_DIR, st.session_state.user, "salary.xlsx"); df = backend.load_excel_safe(mf)
                        if len(df[df["Trạng thái"].str.lower()=="chờ xác nhận"]) > 0:
                            if st.button("✅ XÁC NHẬN ĐÃ NHẬN", key=f"p_{mid}"):
                                df.loc[df["Trạng thái"].str.lower()=="chờ xác nhận", "Trạng thái"] = "đã nhận"; backend.save_excel_safe(df, mf)
                                conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (room_id, my_name, f"✅ Đã nhận đủ: {int(float(content)):,.0f}", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.rerun()
                        else: st.caption("✅ Đã hoàn tất")
                    else: st.caption("⏳ Chờ xác nhận...")
                
                elif mtype == 'image': 
                    if os.path.exists(content): st.image(content, width=250)
                elif mtype == 'call':
                    link = content.split('|')[-1]
                    st.markdown(f"""<div style="background:#e0f2fe; padding:10px; border-radius:10px; width:fit-content; align-self:{align};">📹 <b>{sender}</b> gọi... <br><a href="{link}" target="_blank" style="font-weight:bold;">Tham gia</a></div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="bubble-{'right' if is_me else 'left'}" style="margin-bottom:5px;">{content}</div>""", unsafe_allow_html=True)
                st.caption(ts)
        last_sender = sender
    conn.close()

# ==========================================
# 4. LUỒNG CHÍNH
# ==========================================
if st.session_state.user is None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align:center; color:#0ea5e9'>💎 HỆ THỐNG V45</h1>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Đăng Nhập", "Đăng Ký", "Super Admin"])
        
        conn = backend.get_db_connection(); c = conn.cursor()
        
        with t1:
            u = st.text_input("User"); p = st.text_input("Pass", type="password")
            if st.button("Login", type="primary", use_container_width=True):
                ud = c.execute('SELECT * FROM users WHERE username=? AND password=?', (u, p)).fetchone()
                if ud:
                    st.session_state.user=ud[0]; st.session_state.role=ud[2]; st.session_state.zalo=ud[4]; st.session_state.wp_id=ud[5]; st.session_state.expiry=ud[8]
                    tk = backend.create_login_session(ud[0]); st.query_params["session"] = tk; st.rerun()
                else: st.error("Sai thông tin")
        
        with t2:
            ca, cb = st.columns(2)
            with ca: ru = st.text_input("User ID", key="r1"); rn = st.text_input("Tên hiển thị", key="r2"); rp = st.text_input("SĐT", key="r3")
            with cb: rpass = st.text_input("Pass", type="password", key="r4"); rr = st.radio("Role", ["Nhân viên", "Quản lý"], horizontal=True)
            rwp = "ADMIN"; rk = ""
            if rr == "Nhân viên": rwp = st.text_input("Mã Chi Nhánh")
            elif rr == "Quản lý": rk = st.text_input("Key Admin", type="password")
            
            if st.button("Đăng Ký", use_container_width=True):
                try:
                    if rr=="Nhân viên" and not c.execute("SELECT id FROM workplaces WHERE id=?", (rwp,)).fetchone(): st.error("Mã CN sai!"); st.stop()
                    if rr=="Quản lý":
                        if not c.execute("SELECT key_code FROM license_keys WHERE key_code=? AND status='active'", (rk,)).fetchone(): st.error("Key sai!"); st.stop()
                        c.execute("UPDATE license_keys SET status='used' WHERE key_code=?", (rk,))
                    
                    op = os.path.join(backend.STORAGE_DIR, ru); 
                    if os.path.exists(op): shutil.rmtree(op)
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (ru, rpass, 'admin' if rr=="Quản lý" else 'staff', None, rn, rwp, rp, None, "2099-01-01"))
                    conn.commit(); st.success("OK! Login ngay.")
                except: st.error("User tồn tại")
        
        with t3:
            su = st.text_input("Super User"); sp = st.text_input("Super Pass", type="password")
            if st.button("Super Login", use_container_width=True):
                if su == SUPER_ADMIN_USER and sp == SUPER_ADMIN_PASS:
                    st.session_state.user="SUPER_ADMIN"; st.session_state.role="super_admin"; st.session_state.zalo="System"; st.session_state.wp_id="MASTER"; st.rerun()
                else: st.error("Sai!")
        conn.close()
    st.stop()

# --- APP CHÍNH ---
cu = st.session_state.user; cr = st.session_state.role; cz = st.session_state.zalo; cwp = st.session_state.wp_id
conn = backend.get_db_connection()

with st.sidebar:
    st.image(backend.get_avatar_url(cz), width=100); st.title(cz); st.caption(f"{cu} | {cr}")
    if st.button("Đăng xuất", use_container_width=True):
        if "session" in st.query_params: conn.execute("DELETE FROM sessions WHERE token=?", (st.query_params["session"],)); conn.commit()
        st.query_params.clear(); st.session_state.user=None; st.rerun()

if cr == 'super_admin':
    st.header("🔧 SUPER ADMIN"); t1, t2 = st.tabs(["Key", "Reset"])
    with t1:
        if st.button("Sinh Key"): k=str(uuid.uuid4())[:8].upper(); conn.execute("INSERT INTO license_keys VALUES (?,365,'active')", (k,)); conn.commit(); st.success(k)
        st.dataframe(pd.read_sql("SELECT * FROM license_keys", conn))
    with t2:
        if st.button("RESET ALL"): backend.hard_reset(); st.cache_resource.clear(); st.success("Done!"); st.stop()
    st.stop()

tc, tw = st.tabs(["💬 Chat", "📊 Công Việc"])

with tc:
    aroom = cwp if cr != 'admin' else st.selectbox("Chi nhánh:", [r[0] for r in conn.execute("SELECT id FROM workplaces").fetchall()])
    if aroom:
        render_chat(aroom, cz, cr)
        c1, c2 = st.columns([6,1])
        with c1: 
            if m := st.chat_input("Nhập..."): conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (aroom, cz, m, datetime.now().strftime("%H:%M"), "text")); conn.commit()
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
                if nid and nnm: 
                    try: conn.execute("INSERT INTO workplaces VALUES (?,?,?)", (nid, nnm, cu)); conn.commit(); st.success("OK")
                    except: st.error("Trùng")
        
        sl = conn.execute("SELECT username, zalo_name, workplace_id, phone FROM users WHERE role='staff'").fetchall()
        if sl:
            sel = st.selectbox("NV:", [f"{s[1]} ({s[0]})" for s in sl]); tid = sel.split('(')[1].replace(')', '')
            tf = os.path.join(backend.STORAGE_DIR, tid, "salary.xlsx"); df = backend.load_excel_safe(tf)
            
            pcount = len(df[df["Xác nhận đến"] == False]); debt = pd.to_numeric(df[~df["Trạng thái"].str.contains("đã nhận")]["Tổng lương"], errors='coerce').sum()
            
            c1, c2, c3 = st.columns(3); c1.metric("Nợ", f"{debt:,.0f}"); c2.metric("Chờ duyệt", pcount)
            with c3:
                if pcount > 0 and st.button("Duyệt chấm công"): df.loc[df["Xác nhận đến"]==False, "Xác nhận đến"]=True; backend.save_excel_safe(df, tf); st.rerun()
                if debt > 0 and st.button("Báo chuyển khoản"):
                    df.loc[~df["Trạng thái"].str.contains("đã nhận"), "Trạng thái"] = "chờ xác nhận"; backend.save_excel_safe(df, tf)
                    twp = [s[2] for s in sl if s[0]==tid][0]
                    conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (twp, cz, str(debt), datetime.now().strftime("%H:%M"), "payment_request")); conn.commit(); st.success("Đã báo!"); st.rerun()
            
            with st.expander("Thêm ca"):
                d=st.date_input("Ngày"); v=st.text_input("VT","Tại quán"); t1=st.time_input("In"); t2=st.time_input("Out"); r=st.number_input("Lương",20000)
                if st.button("Lưu"):
                    dt1=datetime.combine(d,t1); dt2=datetime.combine(d,t2); 
                    if dt2<dt1: dt2+=timedelta(days=1)
                    h=(dt2-dt1).seconds/3600; new=pd.DataFrame([{"Ngày":d,"Vị trí":v,"Giờ vào":t1,"Giờ ra":t2,"Tổng lương":h*r,"Trạng thái":"chưa nhận","Xác nhận đến":True}])
                    backend.save_excel_safe(pd.concat([df,new],ignore_index=True), tf); st.success("OK"); st.rerun()
            st.dataframe(df)

    elif cr == 'staff':
        mf = os.path.join(backend.STORAGE_DIR, cu, "salary.xlsx"); dfm = backend.load_excel_safe(mf)
        debt = pd.to_numeric(dfm[~dfm["Trạng thái"].str.contains("đã nhận")]["Tổng lương"], errors='coerce').sum()
        
        st.metric("Quán nợ:", f"{debt:,.0f}")
        if debt > 0 and st.button("Nhắc quản lý"): conn.execute("INSERT INTO messages VALUES (NULL,?,?,?,?,?)", (cwp, cz, f"Check lương: {debt:,.0f}", datetime.now().strftime("%H:%M"), "text")); conn.commit(); st.toast("Sent!")
        
        with st.expander("Báo cáo ca"):
            d=st.date_input("Ngày"); v=st.text_input("VT",cwp); t1=st.time_input("In"); t2=st.time_input("Out"); r=st.number_input("Lương",20000)
            if st.button("Gửi"):
                dt1=datetime.combine(d,t1); dt2=datetime.combine(d,t2); 
                if dt2<dt1: dt2+=timedelta(days=1)
                h=(dt2-dt1).seconds/3600; new=pd.DataFrame([{"Ngày":d,"Vị trí":v,"Giờ vào":t1,"Giờ ra":t2,"Tổng lương":h*r,"Trạng thái":"chưa nhận","Xác nhận đến":False}])
                backend.save_excel_safe(pd.concat([dfm,new],ignore_index=True), mf); st.success("Lưu!"); st.rerun()
        st.dataframe(dfm)

conn.close()