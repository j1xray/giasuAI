import streamlit as st
import os
import time
import random
from datetime import datetime, timezone
from PIL import Image
import google.generativeai as genai
from supabase import create_client
import streamlit.components.v1 as components
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

# ===== 1. CẤU HÌNH UI (SIDEBAR ICON VÔ HÌNH) =====
st.set_page_config(page_title="Gia Sư AI 2.0", page_icon="🧠", layout="wide")

custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background-color: #1E1E2E; color: #CDD6F4; }
header {visibility: hidden;}

/* Sidebar */
[data-testid="stSidebar"] { 
    background-color: #181825; 
    border-right: 1px solid #313244; 
    padding-top: 15px;
}

/* --- ICON VÔ HÌNH GIỐNG FACEBOOK --- */
[data-testid="stSidebar"] div.stButton > button {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 12px 20px !important;
    font-size: 17px !important;
    font-weight: 600 !important;
    color: #CDD6F4 !important;
    border-radius: 10px !important;
    transition: background-color 0.2s ease !important;
    margin-bottom: 2px;
    display: flex !important;
    align-items: center !important;
}
[data-testid="stSidebar"] div.stButton > button:hover {
    background-color: #313244 !important;
    color: #CBA6F7 !important;
}
[data-testid="stSidebar"] div.stButton > button:focus:not(:active) {
    color: #CBA6F7 !important;
    background-color: transparent !important;
}

/* Nút Primary (Đăng nhập, Lưu) */
div.stButton > button[kind="primary"] { background-color: #CBA6F7; color: #11111B; border: none; font-weight: 600; }
div.stButton > button[kind="primary"]:hover { background-color: #F5C2E7; }

/* Ô nhập liệu */
div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea { 
    background-color: #181825 !important; color: #CDD6F4 !important; 
    border: 1px solid #45475A !important; border-radius: 8px !important; 
}

/* Hashtag */
.hashtag-pill {
    display: inline-block;
    background-color: #313244;
    color: #89B4FA;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 600;
    margin-right: 6px;
    margin-top: 8px;
    border: 1px solid #45475A;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ===== 2. KHỞI TẠO =====
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error(f"Lỗi cấu hình Secrets: {e}")
    st.stop()

# ===== 3. BỘ NÃO AI (MODEL ĐANG HOẠT ĐỘNG) =====
@st.cache_resource
def get_tools():
    repl = PythonREPL()
    repl_tool = Tool(name="python_repl", func=repl.run, description="Chạy code Python để tính toán.")
    return [repl_tool]

tools = get_tools()

def create_brain(model_type, system_prompt):
    if model_type == "gemini":
        # Gemini 3.5 Flash Lite - model ổn định
        llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", api_key=st.secrets["GOOGLE_API_KEY"], temperature=0.1)
    else:
        # ĐÃ SỬA: Dùng openai/gpt-oss-120b thay cho qwen đã bị gỡ
        llm = ChatGroq(model="openai/gpt-oss-120b", api_key=st.secrets["GROQ_API_KEY"], temperature=0.1)
    
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
    <div style="background-color: #313244; padding: 40px; border-radius: 16px; max-width: 400px; margin: 80px auto; text-align: center; border: 1px solid #45475A;">
        <h2 style="color: #CBA6F7; margin-bottom: 10px;">Gia Sư AI 2.0</h2>
        <p style="color: #A6ADC8; margin-bottom: 30px;">Học tập thông minh hơn</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        if st.button("🌐 Đăng nhập bằng Google", use_container_width=True):
            try: st.login("google")
            except Exception as e: st.error(f"Lỗi: {e}")
        st.markdown("<div style='text-align:center; color:#A0AEC0; margin:15px 0;'>hoặc</div>", unsafe_allow_html=True)
        guest_name = st.text_input("Tên khách", placeholder="Nhập tên của bạn", label_visibility="collapsed")
        if st.button("👤 Đăng nhập với tư cách Khách", use_container_width=True, type="primary"):
            st.session_state.guest_user = guest_name.strip() if guest_name.strip() else f"Guest_{random.randint(1000, 9999)}"
            st.rerun()
    st.stop()

# ===== 5. USER INFO & ADMIN =====
ADMIN_EMAIL = "j1xray0@gmail.com" # Thay email của bạn vào đây
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

# ===== 6. SIDEBAR (ICON VÔ HÌNH) =====
with st.sidebar:
    col_avt, col_info = st.columns([1, 2.5])
    with col_avt:
        avt_url = user_info.get("avatar_url") or (st.user.picture if st.user.is_logged_in else "")
        if isinstance(avt_url, str) and avt_url.startswith("http"): st.image(avt_url, width=45)
        else: st.write("👤")
    with col_info:
        st.write(f"**{user_info.get('display_name') or username}**")
    
    st.write("")
    st.divider()
    
    if "page" not in st.session_state: st.session_state.page = "Trợ lý AI"
    
    if st.button("🏠  Trang chủ (Trợ lý AI)", use_container_width=True):
        st.session_state.page = "Trợ lý AI"
        st.rerun()
    if st.button("📸  Giải bài qua ảnh", use_container_width=True):
        st.session_state.page = "Giải bài qua ảnh"
        st.rerun()
    if st.button("🎥  Phòng học nhóm", use_container_width=True):
        st.session_state.page = "Phòng học nhóm"
        st.rerun()
    if st.button("📚  Diễn đàn học tập", use_container_width=True):
        st.session_state.page = "Diễn đàn"
        st.rerun()
    if st.button("👤  Hồ sơ cá nhân", use_container_width=True):
        st.session_state.page = "Hồ sơ"
        st.rerun()
    
    st.divider()
    if st.button("🚪  Đăng xuất", use_container_width=True):
        st.session_state.clear()
        if st.user.is_logged_in: st.logout()
        st.rerun()

# ===== 7. HIỂN THỊ CÁC TRANG =====

# --- TRANG 1: TRỢ LÝ AI ---
if st.session_state.page == "Trợ lý AI":
    st.header("Trợ lý AI")
    
    ai_type = st.selectbox("Chọn chế độ Trợ lý", ["Gia sư Toán", "Kỹ sư Code"])
    agent = st.session_state.math_brain if ai_type == "Gia sư Toán" else st.session_state.code_brain
    tab_key = f"chat_{ai_type}"
    
    if f"msgs_{tab_key}" not in st.session_state: st.session_state[f"msgs_{tab_key}"] = []
    for m in st.session_state[f"msgs_{tab_key}"]:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if prompt := st.chat_input(f"Nhập yêu cầu cho {ai_type}..."):
        st.session_state[f"msgs_{tab_key}"].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Đang xử lý..."):
                try:
                    res = agent.invoke({"input": prompt})
                    ans = res["output"]
                except Exception as e: ans = f"Lỗi: {e}"
                st.markdown(ans)
                st.session_state[f"msgs_{tab_key}"].append({"role": "assistant", "content": ans})

# --- TRANG 2: GIẢI BÀI QUA ẢNH ---
elif st.session_state.page == "Giải bài qua ảnh":
    st.header("Giải bài tập qua ảnh")
    st.write("Vui lòng chọn nguồn ảnh. Hệ thống không tự động bật camera để bảo vệ quyền riêng tư.")
    
    img_source = st.radio("Chọn cách tải ảnh:", ["Tải ảnh từ máy", "Chụp ảnh bằng Camera"], horizontal=True, index=0)
    
    image_data = None
    if img_source == "Tải ảnh từ máy":
        image_data = st.file_uploader("Tải ảnh bài tập", type=["jpg", "png", "jpeg"])
    else:
        image_data = st.camera_input("Chụp ảnh bài tập")

    if image_data:
        img = Image.open(image_data)
        st.image(img, width=250, caption="Ảnh đã tải lên")
        
        with st.spinner("Đang phân tích hình ảnh..."):
            model = genai.GenerativeModel('gemini-3.5-flash-lite') 
            res = model.generate_content(["Hãy giải chi tiết bài tập trong ảnh.", img])
            st.markdown("### Kết quả phân tích:")
            st.markdown(res.text)

# --- TRANG 3: PHÒNG HỌC NHÓM ---
elif st.session_state.page == "Phòng học nhóm":
    st.header("Phòng học nhóm")
    
    if "active_room" in st.session_state and st.session_state.active_room:
        st.subheader(f"Đang trong phòng: {st.session_state.active_room}")
        if st.button("Rời phòng", type="primary"):
            st.session_state.active_room = None
            st.rerun()
            
        components.html(f"""
        <div id="jitsi-container" style="width: 100%; height: 500px; margin-top: 20px;"></div>
        <script src="https://meet.jit.si/external_api.js"></script>
        <script>
            new JitsiMeetExternalAPI("meet.jit.si", {{
                roomName: "{st.session_state.active_room}", parentNode: document.querySelector('#jitsi-container'),
                width: "100%", height: 500, userInfo: {{ displayName: "{username}" }}
            }});
        </script>
        """, height=520)
    else:
        col_create, col_list = st.columns([1, 2])
        
        with col_create:
            st.subheader("Tạo phòng mới")
            with st.form("create_room_form"):
                new_room_name = st.text_input("Tên phòng (VD: onthi_toan12)")
                room_privacy = st.radio("Chế độ phòng:", ["Công khai", "Riêng tư"])
                is_public = (room_privacy == "Công khai")
                
                submit_room = st.form_submit_button("Tạo phòng", type="primary")
                if submit_room and new_room_name.strip():
                    try:
                        supabase.table("study_rooms").insert({"room_name": new_room_name, "is_public": is_public, "created_by": username}).execute()
                        st.success("Tạo phòng thành công!")
                    except Exception:
                        st.error("Lỗi: Tên phòng có thể đã tồn tại.")
                        
        with col_list:
            st.subheader("Danh sách phòng công khai")
            try:
                rooms = supabase.table("study_rooms").select("*").eq("is_public", True).execute()
                if not rooms.data:
                    st.info("Chưa có phòng công khai nào.")
                else:
                    for room in rooms.data:
                        with st.container(border=True):
                            col_info, col_btn = st.columns([3, 1])
                            with col_info:
                                st.write(f"**{room['room_name']}**")
                                st.caption(f"Tạo bởi: {room['created_by']}")
                            with col_btn:
                                if st.button("Tham gia", key=f"join_{room['id']}"):
                                    st.session_state.active_room = room['room_name']
                                    st.rerun()
            except: pass

# --- TRANG 4: DIỄN ĐÀN ---
elif st.session_state.page == "Diễn đàn":
    st.header("Diễn đàn học tập")
    
    with st.expander("Đăng bài viết mới"):
        title = st.text_input("Tiêu đề")
        content = st.text_area("Nội dung bài viết")
        tags_input = st.text_input("Hashtag (cách nhau bằng dấu phẩy, VD: toan12, onthi)")
        uploaded_img = st.file_uploader("Đính kèm ảnh (Tùy chọn)", type=["jpg", "png", "jpeg"])
        
        if st.button("Đăng bài", type="primary"):
            if title and content:
                image_url = None
                if uploaded_img:
                    try:
                        f_bytes = uploaded_img.read()
                        f_name = f"forum_{username}_{int(time.time())}.png"
                        supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                        image_url = supabase.storage.from_("public_images").get_public_url(f_name)
                    except Exception as e:
                        st.error(f"Lỗi upload ảnh: {e}")
                
                try:
                    supabase.table("forum_posts").insert({
                        "username": username, "title": title, 
                        "content": content, "tags": tags_input, "image_url": image_url
                    }).execute()
                    st.success("Đăng bài thành công!"); time.sleep(1); st.rerun()
                except: st.error("Lỗi đăng bài!")
            else: st.warning("Vui lòng nhập đủ nội dung.")
            
    st.divider()
    
    try:
        posts = supabase.table("forum_posts").select("*").order("created_at", desc=True).execute()
        for post in posts.data:
            with st.container(border=True):
                st.markdown(f"### {post['title']}")
                st.caption(f"Đăng bởi: **{post['username']}** | {post['created_at'][:10]}")
                st.write(post['content'])
                
                if post.get('image_url'):
                    st.image(post['image_url'], width=400)
                
                if post.get('tags'):
                    tag_list = [t.strip() for t in post['tags'].split(',') if t.strip()]
                    hashtag_html = "".join([f'<span class="hashtag-pill">#{t}</span>' for t in tag_list])
                    st.markdown(hashtag_html, unsafe_allow_html=True)
    except: pass

# --- TRANG 5: HỒ SƠ ---
elif st.session_state.page == "Hồ sơ":
    st.header("Hồ sơ cá nhân")
    
    if not st.session_state.get("edit_profile", False):
        col1, col2 = st.columns([1, 3])
        with col1:
            avt = user_info.get("avatar_url") or (st.user.picture if st.user.is_logged_in else "")
            if isinstance(avt, str) and avt.startswith("http"): st.image(avt, use_column_width=True)
            else: st.write("Chưa có ảnh đại diện")
        with col2:
            st.title(user_info.get("display_name") or username)
            join_date_str = user_info.get('created_at', str(now))[:10]
            join_date = datetime.strptime(join_date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
            st.markdown(f"**Streak:** {user_info.get('streak_count', 1)} ngày | **Tham gia:** {join_date}")
            
            if st.button("Chỉnh sửa hồ sơ"):
                st.session_state.edit_profile = True
                st.rerun()
                
            st.divider()
            dob_str = user_info.get('birth_date')
            dob = datetime.strptime(dob_str, "%Y-%m-%d").strftime("%d/%m/%Y") if dob_str else "Chưa cập nhật"
            st.write(f"**Ngày sinh:** {dob}")
            st.write(f"**Giới tính:** {user_info.get('gender') or 'Chưa cập nhật'}")
            st.write(f"**Giới thiệu:** {user_info.get('bio') or 'Chưa có thông tin.'}")
    else:
        st.subheader("Chỉnh sửa Hồ sơ")
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
            if st.button("Lưu thay đổi", type="primary", use_container_width=True):
                try:
                    upd = {"display_name": new_name, "bio": new_bio, "birth_date": new_dob.strftime("%Y-%m-%d"), "gender": new_gender}
                    if avt_file:
                        f_bytes = avt_file.read()
                        f_name = f"avt_{username}_{int(time.time())}.png"
                        supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                        upd["avatar_url"] = supabase.storage.from_("public_images").get_public_url(f_name)
                    supabase.table("users").update(upd).eq("username", username).execute()
                    st.success("Đã lưu!"); st.session_state.edit_profile = False; time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Lỗi: {e}")
        with col_c:
            if st.button("Hủy", use_container_width=True):
                st.session_state.edit_profile = False
                st.rerun()
