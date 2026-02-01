# styles.py
import streamlit as st

def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');

        /* --- BIẾN MÀU SẮC MESSENGER DARK MODE --- */
        :root {
            --bg-body: #18191a;         /* Nền chính đen xám */
            --bg-sidebar: #242526;      /* Nền sidebar xám hơn chút */
            --bg-card: #242526;         /* Nền các thẻ */
            --text-primary: #e4e6eb;    /* Chữ trắng sáng */
            --text-secondary: #b0b3b8;  /* Chữ xám mờ */
            --bubble-me: #0084ff;       /* Xanh Messenger */
            --bubble-you: #3e4042;      /* Xám bong bóng */
            --input-bg: #3a3b3c;        /* Nền ô nhập liệu */
            --border-color: #393a3b;    /* Viền mờ */
        }

        /* --- CẤU HÌNH CHUNG --- */
        html, body, [class*="css"] {
            font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
            background-color: var(--bg-body) !important;
            color: var(--text-primary) !important;
        }

        /* Ẩn Header/Footer mặc định */
        #MainMenu, footer, header {visibility: hidden;}

        /* --- SIDEBAR --- */
        [data-testid="stSidebar"] {
            background-color: var(--bg-sidebar) !important;
            border-right: 1px solid var(--border-color);
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: var(--text-primary) !important;
        }
        [data-testid="stSidebar"] span {
            color: var(--text-secondary);
        }

        /* --- INPUT FIELDS (Ô nhập liệu tròn như Messenger) --- */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
            background-color: var(--input-bg) !important;
            color: var(--text-primary) !important;
            border-radius: 20px !important;
            border: none !important;
            padding: 10px 15px !important;
        }
        .stTextInput input::placeholder { color: var(--text-secondary); }

        /* --- NÚT BẤM (BUTTONS) --- */
        .stButton > button {
            background-color: var(--input-bg) !important;
            color: var(--text-primary) !important;
            border: none !important;
            border-radius: 20px !important;
            font-weight: 600 !important;
            transition: 0.2s;
        }
        .stButton > button:hover {
            background-color: #4e4f50 !important; /* Sáng hơn khi hover */
        }
        /* Nút chính (Primary) màu xanh */
        .stButton > button[data-testid="baseButton-primary"] {
            background-color: var(--bubble-me) !important;
            color: white !important;
        }

        /* --- KHUNG CHAT (MESSENGER STYLE) --- */
        .chat-container {
            height: 75vh;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            background-color: var(--bg-body); /* Nền đen */
        }

        .message-row {
            display: flex;
            align-items: flex-end; /* Avatar nằm dưới cùng */
            margin-bottom: 10px;
            width: 100%;
        }

        /* Tin nhắn của Tôi (Phải - Xanh) */
        .msg-right { justify-content: flex-end; }
        .bubble-right {
            background-color: var(--bubble-me);
            color: white;
            padding: 10px 15px;
            border-radius: 18px 18px 4px 18px; /* Bo góc đặc trưng */
            max-width: 75%;
            width: fit-content;
            font-size: 15px;
            line-height: 1.4;
            overflow-wrap: anywhere;
        }

        /* Tin nhắn Người khác (Trái - Xám) */
        .msg-left { justify-content: flex-start; }
        .bubble-left {
            background-color: var(--bubble-you);
            color: var(--text-primary);
            padding: 10px 15px;
            border-radius: 18px 18px 18px 4px;
            max-width: 75%;
            width: fit-content;
            font-size: 15px;
            line-height: 1.4;
            overflow-wrap: anywhere;
        }

        .chat-avatar {
            width: 32px; height: 32px; border-radius: 50%;
            margin-right: 8px; object-fit: cover;
        }
        
        .timestamp { font-size: 10px; color: var(--text-secondary); margin-top: 4px; }

        /* --- THẺ THANH TOÁN (Dark Mode) --- */
        .payment-bubble {
            background-color: rgba(34, 197, 94, 0.2); /* Xanh lá trong suốt */
            border: 1px solid #166534;
            color: #86efac; /* Chữ xanh lá sáng */
            padding: 15px;
            border-radius: 15px;
            min-width: 250px;
        }
        .pay-amt { font-size: 24px; font-weight: bold; color: #4ade80; }

        /* --- CARD THỐNG KÊ (Dashboard) --- */
        .metric-card {
            background-color: var(--bg-card);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            border: 1px solid var(--border-color);
        }
        .metric-value { font-size: 28px; font-weight: bold; color: var(--bubble-me); }
        .metric-label { color: var(--text-secondary); font-size: 13px; }

        /* --- LOGIN BOX --- */
        .login-box {
            background-color: var(--bg-card);
            padding: 40px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }
        
        /* Chỉnh màu Tab */
        .stTabs [data-baseweb="tab-list"] {
            background-color: var(--bg-card);
            border-radius: 10px;
            padding: 5px;
        }
        .stTabs [data-baseweb="tab"] { color: var(--text-secondary); }
        .stTabs [aria-selected="true"] { color: var(--bubble-me) !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)