# backend.py
import sqlite3
import pandas as pd
import os
import uuid
import shutil
import zipfile
import io
from datetime import datetime, timedelta

# CẤU HÌNH ĐƯỜNG DẪN
DB_FILE = "system_v47_safe.db"
STORAGE_DIR = "user_files"
UPLOAD_DIR = "chat_uploads"

# KHỞI TẠO THƯ MỤC
if not os.path.exists(STORAGE_DIR): os.makedirs(STORAGE_DIR)
if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)

# --- DATABASE ---
def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, qr_path TEXT, zalo_name TEXT, workplace_id TEXT, phone TEXT, license_key TEXT, expiry_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS workplaces (id TEXT PRIMARY KEY, name TEXT, created_by TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS license_keys (key_code TEXT PRIMARY KEY, duration_days INTEGER, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, workplace_id TEXT, sender TEXT, content TEXT, timestamp TEXT, msg_type TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT, expiry TEXT)''')
    conn.commit()
    conn.close()

# --- BACKUP & RESTORE SYSTEM (TÍNH NĂNG MỚI) ---
def create_backup_zip():
    """Tạo file ZIP chứa toàn bộ dữ liệu hệ thống"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Backup Database
        if os.path.exists(DB_FILE):
            zip_file.write(DB_FILE)
        
        # 2. Backup User Files (Excel lương)
        for root, dirs, files in os.walk(STORAGE_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.join(STORAGE_DIR, os.path.relpath(file_path, STORAGE_DIR)))
                
    buffer.seek(0)
    return buffer

def restore_backup_zip(uploaded_zip):
    """Khôi phục dữ liệu từ file ZIP"""
    try:
        with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
            zip_ref.extractall(".") # Giải nén đè lên thư mục hiện tại
        return True
    except Exception:
        return False

# --- EXCEL ---
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

# --- UTILS ---
def get_avatar_url(name):
    return f"https://ui-avatars.com/api/?name={name}&background=random&color=fff&size=128&bold=true"

def create_login_session(username):
    token = str(uuid.uuid4())
    expiry = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, expiry))
    conn.commit(); conn.close()
    return token

def verify_session_token(token):
    try:
        conn = get_db_connection(); c = conn.cursor()
        r = c.execute("SELECT username, expiry FROM sessions WHERE token=?", (token,)).fetchone()
        conn.close()
        if r and datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S") > datetime.now(): return r[0]
    except: pass
    return None

def hard_reset():
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    if os.path.exists(STORAGE_DIR): shutil.rmtree(STORAGE_DIR); os.makedirs(STORAGE_DIR)
    if os.path.exists(UPLOAD_DIR): shutil.rmtree(UPLOAD_DIR); os.makedirs(UPLOAD_DIR)