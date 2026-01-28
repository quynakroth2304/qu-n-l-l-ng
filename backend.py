# backend.py
import sqlite3
import pandas as pd
import os
import uuid
import shutil
from datetime import datetime, timedelta

# Cấu hình đường dẫn
DB_FILE = "system_v46_modern.db" # Đổi tên DB cho phiên bản mới
STORAGE_DIR = "user_files"
UPLOAD_DIR = "chat_uploads"

# Tự động khởi tạo thư mục
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

# --- EXCEL ---
def load_excel_safe(file_path):
    cols = ["Ngày", "Vị trí", "Giờ vào", "Giờ ra", "Tổng lương", "Trạng thái", "Xác nhận đến"]
    if not os.path.exists(file_path): return pd.DataFrame(columns=cols)
    try:
        df = pd.read_excel(file_path)
        for c in cols: 
            if c not in df.columns: df[c] = ""
        # Đảm bảo trạng thái là chuỗi và không có NaN
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
    # Sử dụng API avatar đẹp hơn, màu sắc ngẫu nhiên
    return f"https://ui-avatars.com/api/?name={name}&background=random&color=fff&size=128&bold=true&format=svg"

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