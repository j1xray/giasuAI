import streamlit as st
import os
import time
import random
import re
import requests
from datetime import datetime, timedelta, timezone
from PIL import Image
import google.generativeai as genai
from supabase import create_client
import streamlit.components.v1 as components
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

# ===== 1. CẤU HÌNH UI =====
st.set_page_config(page_title="Gia Sư AI 2.0", page_icon="🧠", layout="wide")

custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background-color: #1E1E2E; color: #CDD6F4; }
header {visibility: hidden;}
[data-testid="stSidebar"] { background-color: #181825; border-right: 1px solid #313244; }
.login-container {
    background-color: #313244; padding: 40px; border-radius: 16px;
    width: 100%; max-width: 420px; margin: 80px auto; text-align: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}
.login-title { color: #CBA6F7; font-size: 28px; font-weight: 600; margin-bottom: 10px; }
.login-subtitle { color: #A6ADC8; font-size: 14px; margin-bottom: 30px; }
div.stButton > button {
    width: 100%; background-color: #313244; color: #CDD6F4; border: 1px solid #45475A;
    border-radius: 10px; padding: 10px 16px; font-size: 15px; font-weight: 500; transition: all 0.2s;
}
div.stButton > button:hover { background-color: #45475A; color: #CBA6F7; border-color: #CBA6F7; }
div.stButton > button[kind="primary"] { background-color: #CBA6F7; color: #11111B; border: none; }
div.stButton > button[kind="primary"]:hover { background-color: #F5C2E7; color: #11111B; }
div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea { 
    background-color: #181825 !important; color: #CDD6F4 !important; 
    border: 1px solid #45475A !important; border-radius: 8px !important; 
}
div[data-testid="stTextInput"] input:focus { border-color: #CBA6F7 !important; }
.st-key-btn_edit_sidebar button { width: fit-content !important; padding: 2px 12px !important; font-size: 12px !important; border-radius: 20px !important; margin-top: 5px !important; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ===== 2. KHỞI TẠO KẾT NỐI & API KEYS =====
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error(f"❌ Lỗi cấu hình Secrets: {e}")
    st.stop()

# ===== 3. XÂY DỰNG BỘ NÃO (AGENTS) =====
@st.cache_resource
def get_tools():
    search = DuckDuckGoSearchRun()
    search_tool = Tool(name="web_search", func=search.run, description="Tìm kiếm thông tin mới nhất.")
    repl = PythonREPL()
    repl_tool = Tool(name="python_repl", func=repl.run, description="Chạy code Python để tính toán.")
    return [search_tool, repl_tool]

tools = get_tools()

def create_brain(model_type, system_prompt):
    if model_type == "gemini":
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=st.secrets["GOOGLE_API_KEY"], temperature=0.1)
    else:
        llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=st.secrets["GROQ_API_KEY"], temperature=0.1)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt), ("human", "{input}"), ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

if "math_brain" not in st.session_state:
    st.session_state.math_brain = create_brain("gemini", "Bạn là giáo viên Toán. Dùng python_repl để tính chính xác.")
if "code_brain" not in st.session_state:
    st.session_state.code_brain = create_brain("groq", "Bạn là Kỹ sư Phần mềm. Dùng python_repl để chạy thử code.")

# ===== 4. ĐĂNG NHẬP =====
if not st.user.is_logged_in and "guest_user" not in st.session_state:
    st.markdown("""
    <div class="login-container">
        <div class="login-title">Log in or sign up</div>
        <div class="login-subtitle">Học tập thông minh hơn với Gia Sư AI 2.0</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        if st.button("🌐 Đăng nhập Google", use_container_width=True):
            try: st.login("google")
            except Exception as e: st.error(f"Lỗi: {e}")
        st.markdown("<div style='text-align:center; color:#A6ADC8; margin:20px 0;'>HOẶC</div>", unsafe_allow_html=True)
        guest_name = st.text_input("Tên", placeholder="VD: nghia123", label_visibility="collapsed")
        if st.button("Khách", use_container_width=True, type="primary"):
            st.session_state.guest_user = guest_name.strip() if guest_name.strip() else f"Guest_{random.randint(1000, 9999)}"
            st.rerun()
    st.stop()

# ===== 5. LẤY THÔNG TIN USER & ADMIN =====
ADMIN_EMAIL = "j1xray0@gmail.com" # ⚠️ THAY EMAIL ADMIN VÀO ĐÂY
username = st.session_state.get("guest_user") or st.user.email.split('@')[0]
is_admin = (st.user.email == ADMIN_EMAIL) if st.user.is_logged_in else False

now = datetime.now(timezone.utc)
try:
    user_check = supabase.table("users").select("*").eq("username", username).execute()
    if not user_check.data:
        supabase.table("users").insert({"username": username, "password": "oauth", "last_login": now.isoformat(), "created_at": now.isoformat(), "streak_count": 1}).execute()
        user_info = {"streak_count": 1, "created_at": now.isoformat(), "avatar_url": None, "display_name": username}
    else:
        user_info = user_check.data[0]
        # Streak Logic
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

# ===== 6. SIDEBAR =====
with st.sidebar:
    col_avt, col_btn = st.columns([1, 2.5])
    with col_avt:
        avt_url = user_info.get("avatar_url") or (st.user.picture if st.user.is_logged_in else "👤")
        if isinstance(avt_url, str) and avt_url.startswith("http"): st.image(avt_url, width=50)
        else: st.markdown("<h1 style='text-align: center; font-size:50px;'>👤</h1>", unsafe_allow_html=True)
    with col_btn:
        if st.button("✏️ Sửa", key="btn_edit_sidebar"):
            st.session_state.edit_profile = True
            st.rerun()
            
    st.caption("Vai trò: **Admin**" if is_admin else "Vai trò: Học viên")
    
    st.divider()
    st.subheader("👥 Nhóm học tập")
    with st.expander("➕ Tạo nhóm mới"):
        group_name = st.text_input("Tên nhóm")
        if is_admin:
            group_type = st.selectbox("Loại nhóm", ["Cộng đồng (Chỉ Admin)", "Học tập (Mọi người)"])
            type_val = "community" if "Cộng đồng" in group_type else "study"
        else:
            st.info("Chỉ Admin mới có thể tạo nhóm cộng đồng.")
            type_val = "study"
            
        if st.button("Tạo nhóm", use_container_width=True):
            if group_name.strip():
                try:
                    supabase.table("groups").insert({"group_name": group_name, "group_type": type_val, "created_by": username}).execute()
                    st.toast("✅ Đã tạo nhóm!")
                except Exception: st.toast("❌ Lỗi: Tên nhóm đã tồn tại", icon="❌")
            
    if st.button("Đăng xuất", use_container_width=True):
        st.session_state.clear()
        if st.user.is_logged_in: st.logout()
        st.rerun()

# ===== 7. CÁC TABS =====
tab_math, tab_code, tab_vision, tab_room, tab_social, tab_forum, tab_profile = st.tabs([
    "📐 Gia Sư Toán", "💻 Kỹ Sư Code", "📸 Giải Ảnh", "🎥 Phòng Học", "👫 Bạn Bè", "📚 Diễn Đàn", "👤 Hồ Sơ"
])

def render_agent_chat(agent, tab_key, placeholder):
    if f"msgs_{tab_key}" not in st.session_state: st.session_state[f"msgs_{tab_key}"] = []
    for m in st.session_state[f"msgs_{tab_key}"]:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if prompt := st.chat_input(placeholder, key=f"input_{tab_key}"):
        st.session_state[f"msgs_{tab_key}"].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Bộ não đang suy nghĩ..."):
                try:
                    res = agent.invoke({"input": prompt})
                    ans = res["output"]
                except Exception as e: ans = f"Lỗi: {e}"
                st.markdown(ans)
                st.session_state[f"msgs_{tab_key}"].append({"role": "assistant", "content": ans})

# --- TAB 1: TOÁN ---
with tab_math:
    st.subheader("Gia Sư Giải Toán (Tự động tính toán)")
    render_agent_chat(st.session_state.math_brain, "math", "Nhập bài toán (VD: Tính tích phân x^2)")

# --- TAB 2: CODE ---
with tab_code:
    st.subheader("Kỹ Sư Code (Tự động kiểm tra lỗi)")
    render_agent_chat(st.session_state.code_brain, "code", "Nhập yêu cầu code (VD: Viết hàm kiểm tra số nguyên tố)")

# --- TAB 3: GIẢI ẢNH ---
with tab_vision:
    st.subheader("Giải bài tập qua ảnh")
    img_source = st.radio("Nguồn ảnh:", ["Chụp ảnh", "Tải ảnh lên"], horizontal=True)
    image_data = st.camera_input("Chụp bài tập") if img_source == "Chụp ảnh" else st.file_uploader("Tải ảnh", type=["jpg", "png"])
    if image_data:
        img = Image.open(image_data)
        st.image(img, width=300)
        if st.button("Giải bài này"):
            with st.spinner("Đang phân tích..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                res = model.generate_content(["Hãy giải chi tiết bài tập trong ảnh.", img])
                st.markdown(res.text)

# --- TAB 4: PHÒNG HỌC ---
with tab_room:
    st.subheader("Phòng Học Nhóm")
    new_room = st.text_input("Tên phòng (VD: onthi_toan12)")
    if st.button("Vào phòng"):
        components.html(f"""
        <div id="jitsi-container" style="width: 100%; height: 500px;"></div>
        <script src="https://meet.jit.si/external_api.js"></script>
        <script>
            new JitsiMeetExternalAPI("meet.jit.si", {{
                roomName: "{new_room}", parentNode: document.querySelector('#jitsi-container'),
                width: "100%", height: 500, userInfo: {{ displayName: "{username}" }}
            }});
        </script>
        """, height=520)

# --- TAB 5: BẠN BÈ ---
with tab_social:
    st.subheader("Kết Nối Bạn Bè")
    friend_name = st.text_input("Nhập tên người dùng để kết bạn:")
    if st.button("Gửi lời mời"):
        try:
            supabase.table("friendships").insert({"sender": username, "receiver": friend_name}).execute()
            st.toast("✅ Đã gửi lời mời!")
        except: st.toast("Lỗi gửi lời mời.", icon="❌")

# --- TAB 6: DIỄN ĐÀN ---
with tab_forum:
    st.subheader("Diễn Đàn Học Tập")
    with st.expander("➕ Đăng bài thảo luận"):
        title = st.text_input("Tiêu đề")
        content = st.text_area("Nội dung")
        if st.button("Đăng bài"):
            try:
                supabase.table("forum_posts").insert({"username": username, "title": title, "content": content}).execute()
                st.toast("✅ Đăng bài thành công!"); time.sleep(1); st.rerun()
            except: st.toast("Lỗi đăng bài!", icon="❌")
            
    try:
        posts = supabase.table("forum_posts").select("*").order("created_at", desc=True).execute()
        for post in posts.data:
            with st.container(border=True):
                st.markdown(f"### {post['title']}")
                st.caption(f"Đăng bởi: **{post['username']}**")
                st.write(post['content'])
    except: pass

# --- TAB 7: HỒ SƠ ---
with tab_profile:
    if "edit_profile" not in st.session_state: st.session_state.edit_profile = False
    
    if not st.session_state.edit_profile:
        col1, col2 = st.columns([1, 3])
        with col1:
            avt = user_info.get("avatar_url") or (st.user.picture if st.user.is_logged_in else "👤")
            if isinstance(avt, str) and avt.startswith("http"): st.image(avt, use_column_width=True)
            else: st.markdown("<h1 style='text-align: center; font-size: 80px;'>👤</h1>", unsafe_allow_html=True)
        with col2:
            st.title(user_info.get("display_name") or username)
            join_date_str = user_info.get('created_at', str(now))[:10]
            join_date = datetime.strptime(join_date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
            st.markdown(f"🔥 **Streak:** `{user_info.get('streak_count', 1)} ngày` | 📅 **Tham gia:** `{join_date}`")
            st.divider()
            dob_str = user_info.get('birth_date')
            dob = datetime.strptime(dob_str, "%Y-%m-%d").strftime("%d/%m/%Y") if dob_str else "Chưa cập nhật"
            st.write(f"🎂 **Ngày sinh:** {dob}")
            st.write(f"🚻 **Giới tính:** {user_info.get('gender') or 'Chưa cập nhật'}")
            st.write(f"📝 **Giới thiệu:** {user_info.get('bio') or 'Chưa có thông tin.'}")
    else:
        st.subheader("✏️ Chỉnh sửa Hồ sơ")
        avt_file = st.file_uploader("Tải ảnh Avatar mới", type=["jpg", "png"])
        new_name = st.text_input("Tên hiển thị", value=user_info.get("display_name") or username)
        
        col_dob, col_gender = st.columns(2)
        with col_dob:
            default_dob = datetime.strptime(user_info.get("birth_date"), "%Y-%m-%d").date() if user_info.get("birth_date") else datetime(2005, 1, 1).date()
            new_dob = st.date_input("Ngày sinh", value=default_dob, min_value=datetime(1900, 1, 1), max_value=datetime(2026, 12, 31))
        with col_gender:
            gender_opts = ["Nam", "Nữ", "Khác"]
            curr_gender = user_info.get("gender") or "Nam"
            new_gender = st.selectbox("Giới tính", gender_opts, index=gender_opts.index(curr_gender) if curr_gender in gender_opts else 0)
            
        new_bio = st.text_area("Giới thiệu", value=user_info.get("bio") or "")
        
        col_s, col_c = st.columns(2)
        with col_s:
            if st.button("💾 Lưu", type="primary", use_container_width=True):
                try:
                    upd = {"display_name": new_name, "bio": new_bio, "birth_date": new_dob.strftime("%Y-%m-%d"), "gender": new_gender}
                    if avt_file:
                        f_bytes = avt_file.read()
                        f_name = f"avt_{username}_{int(time.time())}.png"
                        supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                        upd["avatar_url"] = supabase.storage.from_("public_images").get_public_url(f_name)
                    supabase.table("users").update(upd).eq("username", username).execute()
                    st.toast("✅ Đã lưu!"); st.session_state.edit_profile = False; time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Lỗi: {e}")
        with col_c:
            if st.button("❌ Hủy", use_container_width=True):
                st.session_state.edit_profile = False
                st.rerun()
