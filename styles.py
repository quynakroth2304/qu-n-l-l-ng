# styles.py
import streamlit as st

def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* CẤU HÌNH MÀU SẮC CHỦ ĐẠO */
        :root {
            --primary: #2563eb;
            --primary-light: #3b82f6;
            --bg-color: #f8fafc;
            --surface: #ffffff;
            --text-main: #1e293b;
            --text-sub: #64748b;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
        }

        #MainMenu, footer, header {visibility: hidden;}

        [data-testid="stSidebar"] {
            background-color: var(--surface);
            border-right: 1px solid #e2e8f0;
        }

        /* CARD DASHBOARD */
        .metric-card {
            background: var(--surface);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            text-align: center;
            transition: transform 0.2s;
        }
        .metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .metric-value { font-size: 28px; font-weight: 700; color: var(--primary); margin-bottom: 5px; }
        .metric-label { font-size: 13px; color: var(--text-sub); font-weight: 600; text-transform: uppercase; }

        /* KHUNG CHAT (FIXED) */
        .chat-container {
            padding: 20px;
            background: var(--surface);
            border-radius: 16px;
            height: 78vh;
            overflow-y: auto;
            border: 1px solid #e2e8f0;
            display: flex;
            flex-direction: column;
        }
        
        .message-row {
            display: flex;
            align-items: flex-end;
            margin-bottom: 12px;
            width: 100%;
        }

        /* BONG BÓNG CHAT (CHỐNG VỠ KHUNG TUYỆT ĐỐI) */
        .bubble {
            padding: 10px 16px;
            border-radius: 18px;
            display: inline-block;
            max-width: 80%;
            min-width: 30px;
            text-align: left;
            
            /* Thuộc tính quan trọng để xuống dòng */
            overflow-wrap: anywhere; 
            word-break: break-word;
            white-space: pre-wrap;
            
            font-size: 15px;
            line-height: 1.5;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .msg-right { justify-content: flex-end; }
        .bubble-right {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }

        .msg-left { justify-content: flex-start; }
        .bubble-left {
            background: #f1f5f9;
            color: var(--text-main);
            border-bottom-left-radius: 4px;
            border: 1px solid #e2e8f0;
        }
        
        .chat-avatar {
            width: 36px; height: 36px; border-radius: 50%;
            margin-right: 8px; flex-shrink: 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        /* THẺ THANH TOÁN */
        .payment-card {
            background: #ecfdf5; border: 1px solid #86efac;
            color: #14532d; padding: 15px; border-radius: 12px;
            min-width: 250px; text-align: left;
        }
        .pay-amt { font-size: 24px; font-weight: 800; color: #16a34a; margin: 5px 0; }

        /* BUTTONS */
        .stButton > button {
            border-radius: 8px; font-weight: 600; border: none; padding: 0.5rem 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: 0.2s;
        }
        .stButton > button:hover { opacity: 0.9; transform: translateY(-1px); }
        
        /* LOGIN CARD */
        .login-box {
            background: white; padding: 40px; border-radius: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1); border: 1px solid #e2e8f0;
        }
    </style>
    """, unsafe_allow_html=True)