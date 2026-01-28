# styles.py
import streamlit as st

def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #f0f2f5;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e0e0e0;
        }

        /* CARD THỐNG KÊ */
        .metric-card {
            background: white; border-radius: 12px; padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #f0f0f0;
            text-align: center; margin-bottom: 10px;
        }
        .metric-value { font-size: 28px; font-weight: 700; color: #0ea5e9; margin-bottom: 5px; }
        .metric-label { font-size: 13px; color: #64748b; font-weight: 600; text-transform: uppercase; }

        /* KHUNG CHAT */
        .chat-container {
            padding: 20px;
            background: white;
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
            margin-bottom: 10px;
            width: 100%;
        }

        /* Tin nhắn */
        .message-right { justify-content: flex-end; }
        .bubble-right {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            color: white; padding: 10px 16px; border-radius: 18px 18px 4px 18px;
            display: inline-block; max-width: 80%; min-width: 20px;
            text-align: left; 
            overflow-wrap: anywhere;
            word-break: break-word; 
            white-space: pre-wrap;
            font-size: 15px; line-height: 1.5;
            box-shadow: 0 2px 5px rgba(37, 99, 235, 0.2);
        }

        .message-left { justify-content: flex-start; }
        .bubble-left {
            background: #f1f5f9; color: #1e293b; padding: 10px 16px;
            border-radius: 18px 18px 18px 4px;
            display: inline-block; max-width: 80%; min-width: 20px;
            text-align: left; 
            overflow-wrap: anywhere;
            word-break: break-word; 
            white-space: pre-wrap;
            font-size: 15px; line-height: 1.5; border: 1px solid #e2e8f0;
        }
        
        .chat-avatar {
            width: 36px; height: 36px; border-radius: 50%;
            margin-right: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex-shrink: 0;
        }

        /* Payment Bubble */
        .payment-bubble {
            background: #ecfdf5; border: 1px solid #10b981; color: #064e3b;
            padding: 15px; border-radius: 12px; min-width: 250px;
        }
        .payment-header { font-weight: bold; font-size: 14px; display: flex; align-items: center; gap: 5px; }
        .payment-amount { font-size: 24px; font-weight: 800; color: #059669; margin: 5px 0; }

        /* Button */
        .stButton > button {
            border-radius: 8px; font-weight: 600; border: none; padding: 0.5rem 1rem;
            transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stButton > button:hover { opacity: 0.9; transform: translateY(-1px); }
    </style>
    """, unsafe_allow_html=True)