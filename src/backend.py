import requests
import base64
import streamlit as st
import streamlit as st
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from supabase import create_client
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

ADMIN_EMAIL = "j1xray0@gmail.com" # ⚠️ THAY EMAIL CỦA BẠN

@st.cache_resource
def init_connections():
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    return supabase

@st.cache_resource
def init_ai_brains():
    tools = [Tool(name="python_repl", func=PythonREPL().run, description="Chạy code Python.")]
    
    prompt_math = ChatPromptTemplate.from_messages([("system", "Bạn là giáo viên Toán. Dùng python_repl để tính chính xác."), ("human", "{input}"), ("placeholder", "{agent_scratchpad}")])
    llm_math = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", api_key=st.secrets["GOOGLE_API_KEY"], temperature=0.1)
    math_brain = AgentExecutor(agent=create_tool_calling_agent(llm_math, tools, prompt_math), tools=tools, verbose=True)
    
    prompt_code = ChatPromptTemplate.from_messages([("system", "Bạn là Kỹ sư Phần mềm. Dùng python_repl để chạy thử code."), ("human", "{input}"), ("placeholder", "{agent_scratchpad}")])
    llm_code = ChatGroq(model="openai/gpt-oss-120b", api_key=st.secrets["GROQ_API_KEY"], temperature=0.1)
    code_brain = AgentExecutor(agent=create_tool_calling_agent(llm_code, tools, prompt_code), tools=tools, verbose=True)
    
    return math_brain, code_brain

def get_user_data(supabase, username, is_logged_in):
    now = datetime.now(timezone.utc)
    today_date = now.date().isoformat()
    user_info = {}
    
    try:
        user_check = supabase.table("users").select("*").eq("username", username).execute()
        if not user_check.data:
            supabase.table("users").insert({"username": username, "password": "oauth", "last_login": now.isoformat(), "created_at": now.isoformat(), "streak_count": 1}).execute()
            user_info = {"streak_count": 1, "created_at": now.isoformat(), "avatar_url": None, "display_name": username, "is_premium": False, "daily_questions": 0, "last_active_date": today_date}
        else:
            user_info = user_check.data[0]
            if user_info.get("last_active_date") != today_date:
                supabase.table("users").update({"daily_questions": 0, "last_active_date": today_date}).eq("username", username).execute()
                user_info["daily_questions"] = 0
                user_info["last_active_date"] = today_date
                
            last_login_str = user_info.get("last_login")
            if last_login_str:
                last_login = datetime.fromisoformat(last_login_str.replace('Z', '+00:00'))
                days_diff = (now.date() - last_login.date()).days
                if days_diff == 1:
                    new_streak = user_info.get("streak_count", 1) + 1
                    supabase.table("users").update({"last_login": now.isoformat(), "streak_count": new_streak}).eq("username", username).execute()
                    user_info["streak_count"] = new_streak
                elif days_diff > 1:
                    supabase.table("users").update({"last_login": now.isoformat(), "streak_count": 1}).eq("username", username).execute()
                    user_info["streak_count"] = 1
    except: pass
    return user_info

def create_payment_link(username, amount=10000):
    """Tạo link thanh toán qua ApiPay"""
    # Lấy key từ Secrets
    access_key = st.secrets.get("APIPAY_ACCESS_KEY", "")
    secret_key = st.secrets.get("APIPAY_SECRET_KEY", "")
    
    if not access_key or not secret_key:
        return {"error": "Chưa cấu hình ApiPay Key trong Secrets"}

    # Tạo chuỗi xác thực Basic Auth
    auth_str = f"{access_key}:{secret_key}"
    auth_base64 = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Bearer {auth_base64}",
        "Content-Type": "application/json"
    }
    
    # Nội dung chuyển khoản (Mã đơn hàng)
    order_code = f"UPGRADE_{username}_{int(datetime.now().timestamp())}"
    
    payload = {
        "bankPublicId": "bank_abc123",  # ⚠️ BẠN CẦN THAY MÃ NGÂN HÀNG MB CỦA BẠN TRÊN APIPAY VÀO ĐÂY
        "amount": amount,
        "content": order_code
    }
    
    try:
        response = requests.post("https://app.apipay.vn/v1/client/payment-requests", json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()  # Trả về link thanh toán (payUrl)
        else:
            return {"error": f"Lỗi ApiPay: {response.text}"}
    except Exception as e:
        return {"error": str(e)}
