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

ADMIN_EMAIL = "j1xray0@gmail.com" # THAY EMAIL ADMIN VÀO ĐÂY

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
    except: pass
    return user_info

# HÀM LƯU LỊCH SỬ CHAT & GỬI TIN NHẮN
def send_message(supabase, sender, content, receiver=None, group_id=None, file_url=None, msg_type="text"):
    supabase.table("messages").insert({
        "sender": sender, "receiver": receiver, "group_id": group_id,
        "content": content, "file_url": file_url, "msg_type": msg_type
    }).execute()

def get_messages(supabase, receiver=None, group_id=None):
    if group_id:
        res = supabase.table("messages").select("*").eq("group_id", group_id).order("created_at").execute()
    else:
        # Lấy tin nhắn giữa user A và user B (cả 2 chiều)
        # Vì Supabase không hỗ trợ query phức tạp dễ dàng, ta lấy tất cả rồi lọc (với dữ liệu nhỏ thì ok)
        res = supabase.table("messages").select("*").execute()
        data = [m for m in res.data if (m['sender'] == st.session_state.username and m['receiver'] == receiver) or (m['sender'] == receiver and m['receiver'] == st.session_state.username)]
        return data
    return res.data

# AI FALLBACK (Nếu Gemini lỗi, tự động dùng Llama)
def get_ai_response_fallback(prompt, image=None):
    try:
        # Thử Gemini trước
        model = genai.GenerativeModel('gemini-3.5-flash-lite')
        content = [prompt]
        if image: content.append(image)
        return model.generate_content(content).text
    except Exception as e:
        print("Gemini lỗi, chuyển sang Llama:", e)
        try:
            # Fallback sang Groq
            import openai
            client = openai.OpenAI(api_key=st.secrets["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
            res = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": prompt}])
            return res.choices[0].message.content
        except:
            return "Hệ thống AI đang quá tải, vui lòng thử lại sau."
