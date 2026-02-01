# backend.py
import sqlite3
import pandas as pd
import os
import uuid
import shutil
import zipfile
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime, timedelta

# --- CẤU HÌNH EMAIL (ĐIỀN ĐÚNG CỦA BẠN VÀO ĐÂY) ---
EMAIL_SENDER = "email_cua_ban@gmail.com"
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"
EMAIL_RECEIVER = "email_cua_ban@gmail.com"

DB_FILE = "system_v52_dark.db"
STORAGE_DIR = "user_files"
UPLOAD_DIR = "chat_uploads"

if not os.path.exists(STORAGE_DIR): os.makedirs(STORAGE_DIR)
if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)

# --- DATABASE ---
def get_db_connection(): return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_db_connection(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT, license_key TEXT, expiry_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS workplaces (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS license_keys (key_code TEXT PRIMARY KEY, duration_days INTEGER, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, workplace_id TEXT, sender TEXT, content TEXT, timestamp TEXT, msg_type TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT, expiry TEXT)''')
    conn.commit(); conn.close()

# --- BACKUP ---
def create_backup_zip_bytes():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        if os.path.exists(DB_FILE): zip_file.write(DB_FILE)
        for root, dirs, files in os.walk(STORAGE_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.join(STORAGE_DIR, os.path.relpath(file_path, STORAGE_DIR)))
    buffer.seek(0); return buffer

def restore_backup(uploaded_file):
    try:
        with zipfile.ZipFile(uploaded_file, 'r') as z: z.extractall(".")
        return True
    except: return False

def send_auto_backup_email(trigger="Auto"):
    try:
        msg = MIMEMultipart(); msg['From']=EMAIL_SENDER; msg['To']=EMAIL_RECEIVER
        msg['Subject']=f"Backup {datetime.now().strftime('%d/%m')}"
        msg.attach(MIMEText(f"Trigger: {trigger}", 'plain'))
        part=MIMEBase('application',"octet-stream")
        part.set_payload(create_backup_zip_bytes().getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="backup.zip"')
        msg.attach(part)
        s=smtplib.SMTP('smtp.gmail.com',587); s.starttls()
        s.login(EMAIL_SENDER, EMAIL_PASSWORD); s.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string()); s.quit()
        return True
    except: return False

# --- UTILS ---
def load_excel_safe(path):
    cols=["Ngày","Vị trí","Giờ vào","Giờ ra","Tổng lương","Trạng thái","Xác nhận đến"]
    if not os.path.exists(path): return pd.DataFrame(columns=cols)
    try:
        df=pd.read_excel(path)
        for c in cols: 
            if c not in df.columns: df[c]=""
        df["Trạng thái"]=df["Trạng thái"].fillna("chưa nhận").astype(str)
        df["Xác nhận đến"]=df["Xác nhận đến"].fillna(False)
        return df
    except: return pd.DataFrame(columns=cols)

def save_excel_safe(df, path):
    d=os.path.dirname(path); 
    if d and not os.path.exists(d): os.makedirs(d)
    df.to_excel(path, index=False)

def get_avatar_url(name): return f"https://ui-avatars.com/api/?name={name}&background=random&color=fff&size=128&bold=true"

# --- SESSION ---
def create_login_session(u):
    tk=str(uuid.uuid4()); exp=(datetime.now()+timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    c=get_db_connection(); c.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (tk,u,exp)); c.commit(); c.close()
    return tk

def verify_session_token(tk):
    try:
        c=get_db_connection(); r=c.execute("SELECT username, expiry FROM sessions WHERE token=?", (tk,)).fetchone(); c.close()
        if r and datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S") > datetime.now(): return r[0]
    except: pass
    return None

def hard_reset():
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    if os.path.exists(STORAGE_DIR): shutil.rmtree(STORAGE_DIR); os.makedirs(STORAGE_DIR)