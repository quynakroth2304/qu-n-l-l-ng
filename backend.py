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

# --- CẤU HÌNH EMAIL ---
EMAIL_SENDER = "quynakroth2304@gmail.com"
EMAIL_PASSWORD = "iowl ubie lpmg glfd"
EMAIL_RECEIVER = "quynakroth2304@gmail.com"

DB_FILE = "system_v48_auto.db"
STORAGE_DIR = "user_files"
UPLOAD_DIR = "chat_uploads"

# Tự động tạo thư mục
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

# --- BACKUP SYSTEM (NÉN & GIẢI NÉN) ---
def create_backup_zip_bytes():
    """Nén toàn bộ dữ liệu thành bytes để tải về"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Nén Database
        if os.path.exists(DB_FILE):
            zip_file.write(DB_FILE)
        
        # 2. Nén thư mục User Files (Excel)
        for root, dirs, files in os.walk(STORAGE_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                # Lưu cấu trúc thư mục tương đối
                zip_file.write(file_path, os.path.join(STORAGE_DIR, os.path.relpath(file_path, STORAGE_DIR)))
                
    buffer.seek(0)
    return buffer

def restore_backup_from_zip(uploaded_zip_file):
    """Khôi phục dữ liệu từ file ZIP tải lên"""
    try:
        with zipfile.ZipFile(uploaded_zip_file, 'r') as zip_ref:
            zip_ref.extractall(".") # Giải nén đè lên thư mục hiện tại
        return True
    except Exception as e:
        print(f"Lỗi restore: {e}")
        return False

def send_auto_backup_email(trigger_action="Auto Backup"):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER; msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f"[BACKUP] {datetime.now().strftime('%d/%m %H:%M')}"
        msg.attach(MIMEText(f"Sao lưu tự động: {trigger_action}", 'plain'))
        
        zip_buffer = create_backup_zip_bytes()
        part = MIMEBase('application', "octet-stream")
        part.set_payload(zip_buffer.getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="backup.zip"')
        msg.attach(part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls(); server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string()); server.quit()
        return True
    except: return False

# --- EXCEL & FILE ---
def load_excel_safe(file_path):
    cols = ["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]
    if not os.path.exists(file_path): return pd.DataFrame(columns=cols)
    try:
        df = pd.read_excel(file_path)
        for c in cols: 
            if c not in df.columns: df[c] = ""
        df["Trạng thái"] = df["Trạng thái"].fillna("chưa nhận").astype(str)
        df["Xác nhận đến"] = df["Xác nhận đến"].fillna(False)
        return df
    except: return pd.DataFrame(columns=cols)

def save_excel_safe(dataframe, file_path):
    d = os.path.dirname(file_path)
    if d and not os.path.exists(d): os.makedirs(d)
    dataframe.to_excel(file_path, index=False)

def get_avatar_url(name): return f"https://ui-avatars.com/api/?name={name}&background=random&color=fff&size=128&bold=true"

# --- SESSION ---
def create_login_session(username):
    token = str(uuid.uuid4()); expiry = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, expiry))
    conn.commit(); conn.close()
    return token

def verify_session_token(token):
    try:
        conn = get_db_connection(); c = conn.cursor()
        r = c.execute("SELECT username, expiry FROM sessions WHERE token=?", (token,)).fetchone(); conn.close()
        if r and datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S") > datetime.now(): return r[0]
    except: pass
    return None

def hard_reset():
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    if os.path.exists(STORAGE_DIR): shutil.rmtree(STORAGE_DIR); os.makedirs(STORAGE_DIR)
    if os.path.exists(UPLOAD_DIR): shutil.rmtree(UPLOAD_DIR); os.makedirs(UPLOAD_DIR)