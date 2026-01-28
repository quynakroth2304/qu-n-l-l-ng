# styles.py
import streamlit as st

def load_css():
    st.markdown("""
    <style>
        /* IMPORT FONT INTER */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* --- CẤU HÌNH CHUNG --- */
        :root {
            --primary-color: #0ea5e9; /* Xanh dương chính */
            --primary-dark: #0284c7;
            --secondary-bg: #f8fafc; /* Xám nền rất nhạt */
            --text-dark: #1e293b;
            --text-gray: #64748b;
            --success-color: #22c55e;
            --danger-color: #ef4444;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --radius-md: 12px;
            --radius-lg: 16px;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: var(--secondary-bg) !important;
            color: var(--text-dark);
        }

        /* Ẩn các thành phần mặc định của Streamlit */
        #MainMenu, footer, header {visibility: hidden;}

        /* Tùy chỉnh Sidebar */
        [data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #e2e8f0;
            box-shadow: var(--shadow-sm);
        }

        /* Tùy chỉnh Container chính */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 1200px;
        }

        /* --- CARD THỐNG KÊ (Dashboard) --- */
        .metric-card {
            background: white;
            border-radius: var(--radius-lg);
            padding: 24px;
            box-shadow: var(--shadow-sm);
            border: 1px solid #f1f5f9;
            text-align: center;
            transition: all 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-md);
        }
        .metric-value {
            font-size: 32px;
            font-weight: 800;
            color: var(--primary-color);
            margin-bottom: 8px;
        }
        .metric-label {
            font-size: 14px;
            color: var(--text-gray);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* --- NÚT BẤM (Buttons) --- */
        /* Nút chính (Primary) */
        .stButton > button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 6px rgba(14, 165, 233, 0.3);
        }
        /* Nút thường */
        .stButton > button {
            border-radius: var(--radius-md) !important;
            font-weight: 600 !important;
            padding: 0.6rem 1.2rem !important;
            transition: all 0.2s ease-in-out !important;
            border: 1px solid #e2e8f0;
            background-color: white;
            color: var(--text-dark);
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md) !important;
            border-color: var(--primary-color);
        }

        /* --- INPUT FIELDS & SELECTBOX --- */
        .stTextInput > div > div > input, .stSelectbox > div > div > div, .stDateInput > div > div > input, .stTimeInput > div > div > input, .stNumberInput > div > div > input {
            border-radius: var(--radius-md) !important;
            border: 1px solid #e2e8f0 !important;
            padding: 0.5rem 1rem !important;
            background-color: white !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: var(--primary-color) !important;
            box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.2) !important;
        }

        /* --- KHUNG CHAT --- */
        .chat-container {
            padding: 25px;
            background: #ffffff;
            border-radius: var(--radius-lg);
            height: 75vh;
            overflow-y: auto;
            border: 1px solid #e2e8f0;
            display: flex;
            flex-direction: column;
            box-shadow: var(--shadow-sm);
        }
        
        .message-row {
            display: flex;
            align-items: flex-end;
            margin-bottom: 16px; /* Tăng khoảng cách giữa các tin */
            width: 100%;
        }

        /* Tin nhắn Phải (Tôi) */
        .message-right { justify-content: flex-end; }
        .bubble-right {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); /* Gradient xanh đậm hơn */
            color: white;
            padding: 12px 18px;
            border-radius: 20px 20px 4px 20px;
            display: inline-block;
            max-width: 80%;
            min-width: 40px;
            text-align: left;
            overflow-wrap: anywhere;
            word-break: break-word;
            white-space: pre-wrap;
            font-size: 15px;
            line-height: 1.5;
            box-shadow: 0 4px 8px rgba(37, 99, 235, 0.25);
        }

        /* Tin nhắn Trái (Người khác) */
        .message-left { justify-content: flex-start; }
        .bubble-left {
            background: #f1f5f9;
            color: var(--text-dark);
            padding: 12px 18px;
            border-radius: 20px 20px 20px 4px;
            display: inline-block;
            max-width: 80%;
            min-width: 40px;
            text-align: left;
            overflow-wrap: anywhere;
            word-break: break-word;
            white-space: pre-wrap;
            font-size: 15px;
            line-height: 1.5;
            border: 1px solid #e2e8f0;
        }
        
        .chat-avatar {
            width: 40px; height: 40px; /* Avatar lớn hơn chút */
            border-radius: 50%;
            margin-right: 12px;
            box-shadow: var(--shadow-sm);
            flex-shrink: 0;
            border: 2px solid white;
        }
        
        .chat-timestamp {
            font-size: 11px;
            color: #94a3b8;
            margin-top: 4px;
        }

        /* --- PAYMENT BUBBLE (Thẻ thanh toán) --- */
        .payment-bubble {
            background: #f0fdf4; /* Xanh lá siêu nhạt */
            border: 1px solid #bbf7d0;
            color: #166534;
            padding: 18px;
            border-radius: 16px;
            min-width: 260px;
            box-shadow: 0 4px 6px -1px rgba(34, 197, 94, 0.1);
        }
        .payment-header { font-weight: 700; font-size: 15px; display: flex; align-items: center; gap: 8px; color: #15803d; }
        .payment-amount { font-size: 26px; font-weight: 800; color: #16a34a; margin: 10px 0; }

        /* --- LOGIN CARD --- */
        .login-card {
            background: white;
            padding: 40px;
            border-radius: 24px;
            box-shadow: var(--shadow-md);
            border: 1px solid #f0f0f0;
        }
    </style>
    """, unsafe_allow_html=True)