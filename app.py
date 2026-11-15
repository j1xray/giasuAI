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

# ===== 1. CẤU HÌNH UI (SOFT DARK MODE & FONTAWESOME) =====
st.set_page_config(page_title="Gia Sư AI 2.0", page_icon="🧠", layout="wide")

custom_css = """
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background-color: #1E1E2E; color: #CDD6F4; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {background: transparent !important;}

/* Sidebar tổng thể */
[data-testid="stSidebar"] { 
    background-color: #181825; 
    border-right: 1px solid #313244; 
    padding-top: 15px;
}

/* Nút Menu với Icon FontAwesome (Ẩn nền, chỉ hiện icon và chữ) */
[data-testid="stSidebar"] div.stButton > button {
    background-color: transparent !important;
    border: none !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 10px 15px !important;
    font-size: 16px !important;
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
[data-testid="stSidebar"] div.stButton > button:before {
    margin-right: 12px;
    font-family: "Font Awesome 6 Free"; 
    font-weight: 900;
    font-size: 18px;
}
/* Gán Icon cho từng nút dựa trên thứ tự */
[data-testid="stSidebar"] div.stButton > button:nth-of-type(1)::before { content: "\\f015"; } /* Home */
[data-testid="stSidebar"] div.stButton > button:nth-of-type(2)::before { content: "\\f0c0"; } /* Users */
[data-testid="stSidebar"] div.stButton > button:nth-of-type(3)::before { content: "\\f03d"; } /* Camera */
[data-testid="stSidebar"] div.stButton > button:nth-of-type(4)::before { content: "\\f008"; } /* Video/Phòng */
[data-testid="stSidebar"] div.stButton > button:nth-of-type(5)::before { content: "\\f086"; } /* Comments/Forum */
[data-testid="stSidebar"] div.stButton > button:nth-of-type(6)::before { content: "\\f007"; } /* User/Profile */

/* Khối Profile Gọn Gàng */
.profile-container {
    display: flex; align-items: center; gap: 12px; padding: 10px;
    background-color: #313244; border-radius: 10px; margin-bottom: 15px;
}
.profile-avatar { width: 50px; height: 50px; border-radius: 50%; object-fit: cover; border: 2px solid #CBA6F7; }
.profile-name { font-weight: 600; font-size: 16px; color: #CDD6F4; }
.profile-username { font-size: 12px; color: #A6ADC8; }

/* Nút Primary (Nâng cấp, Lưu) */
div.stButton > button[kind="primary"] { background-color: #CBA6F7; color: #11111B; border: none; font-weight: 600; }
div.stButton > button[kind="primary"]:hover { background-color: #F5C2E7; }

/* Ô nhập liệu */
div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea { 
    background-color: #181825 !important; color: #CDD6F4 !important; 
    border: 1px solid #45475A !important; border-radius: 8px !important; 
}

/* Hashtag */
.hashtag-pill {
    display: inline-block; background-color: #313244; color: #89B4FA;
    padding: 4px 12px; border-radius: 16px; font-size: 13px;
    font-weight: 600; margin-right: 6px; margin-top: 8px; border: 1px solid #45475A;
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

# ===== 3. BỘ NÃO AI =====
@st.cache_resource
def get_tools():
    repl = PythonREPL()
    repl_tool = Tool(name="python_repl", func=repl.run, description="Chạy code Python.")
    return [repl_tool]

tools = get_tools()

def create_brain(model_type, system_prompt):
    if model_type == "gemini":
        llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", api_key=st.secrets["GOOGLE_API_KEY"], temperature=0.1)
    else:
        llm = ChatGroq(model="openai/gpt-oss-120b", api_key=st.secrets["GROQ_API_KEY"], temperature=0.1)
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}"), ("placeholder", "{agent_scratchpad}")])
    return AgentExecutor(agent=create_tool_calling_agent(llm, tools, prompt), tools=tools, verbose=True)

if "math_brain" not in st.session_state:
    st.session_state.math_brain = create_brain("gemini", "Bạn là giáo viên Toán. Dùng python_repl để tính chính xác.")
if "code_brain" not in st.session_state:
    st.session_state.code_brain = create_brain("groq", "Bạn là Kỹ sư Phần mềm. Dùng python_repl để chạy thử code.")

# ===== 4. ĐĂNG NHẬP =====
if not st.user.is_logged_in and "guest_user" not in st.session_state:
    st.markdown("""
    <div style="background-color: #313244; padding: 40px; border-radius: 16px; max-width: 400px; margin: 80px auto; text-align: center; border: 1px solid #45475A;">
        <h2 style="color: #CBA6F7; margin-bottom: 10px;">Gia Sư AI 2.0</h2>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        if st.button("Đăng nhập bằng Google", use_container_width=True):
            try: st.login("google")
            except Exception as e: st.error(f"Lỗi: {e}")
        guest_name = st.text_input("Tên khách", placeholder="Nhập tên của bạn", label_visibility="collapsed")
        if st.button("Đăng nhập Khách", use_container_width=True, type="primary"):
            st.session_state.guest_user = guest_name.strip() if guest_name.strip() else f"Guest_{random.randint(1000, 9999)}"
            st.rerun()
    st.stop()

# ===== 5. USER INFO & ADMIN =====
ADMIN_EMAIL = "j1xray0@gmail.com" # ⚠️ THAY EMAIL CỦA BẠN
username = st.session_state.get("guest_user") or st.user.email.split('@')[0]
is_admin = (st.user.email == ADMIN_EMAIL) if st.user.is_logged_in else False

now = datetime.now(timezone.utc)
today_date = now.date().isoformat()

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
except Exception as e:
    st.error(f"Lỗi DB: {e}")

is_premium = user_info.get("is_premium", False)
daily_questions = user_info.get("daily_questions", 0)

# ===== 6. HEADER & THANH TOÁN =====
col_header, col_btn = st.columns([8, 2])
with col_btn:
    if is_premium:
        st.success("Gói Premium")
    else:
        st.info(f"Bản Free (Câu hỏi: {daily_questions}/10)")
        if st.button("Nâng cấp (10k/tháng)", type="primary", use_container_width=True):
            st.info("Đang chuyển hướng đến cổng thanh toán Alipay...")
            time.sleep(1)
            supabase.table("users").update({"is_premium": True}).eq("username", username).execute()
            st.success("Thanh toán thành công! Đã nâng cấp Premium.")
            time.sleep(2)
            st.rerun()

# ===== 7. SIDEBAR =====
with st.sidebar:
    avt_url = user_info.get("avatar_url") or (st.user.picture if st.user.is_logged_in else "https://api.dicebear.com/7.x/avataaars/svg?seed=" + username)
    disp_name = user_info.get('display_name') or username
    
    st.markdown(f"""
    <div class="profile-container">
        <img src="{avt_url}" class="profile-avatar">
        <div>
            <div class="profile-name">{disp_name}</div>
            <div class="profile-username">@{username}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    if "page" not in st.session_state: st.session_state.page = "Trợ lý AI"
    
    # Các nút này sẽ tự động nhận Icon FontAwesome từ CSS ở trên
    if st.button("Trợ lý AI", use_container_width=True): st.session_state.page = "Trợ lý AI"; st.rerun()
    if st.button("Nhóm học tập", use_container_width=True): st.session_state.page = "Nhóm"; st.rerun()
    if st.button("Giải bài qua ảnh", use_container_width=True): st.session_state.page = "Giải bài qua ảnh"; st.rerun()
    if st.button("Phòng học nhóm", use_container_width=True): st.session_state.page = "Phòng học nhóm"; st.rerun()
    if st.button("Diễn đàn", use_container_width=True): st.session_state.page = "Diễn đàn"; st.rerun()
    if st.button("Hồ sơ", use_container_width=True): st.session_state.page = "Hồ sơ"; st.rerun()
    
    st.divider()
    if st.button("Đăng xuất", use_container_width=True):
        st.session_state.clear()
        if st.user.is_logged_in: st.logout()
        st.rerun()

# ===== 8. HIỂN THỊ CÁC TRANG =====

# --- TRANG 1: TRỢ LÝ AI ---
if st.session_state.page == "Trợ lý AI":
    st.header("Trợ lý AI")
    ai_type = st.selectbox("Chọn chế độ", ["Gia sư Toán", "Kỹ sư Code"])
    agent = st.session_state.math_brain if ai_type == "Gia sư Toán" else st.session_state.code_brain
    tab_key = f"chat_{ai_type}"
    
    if f"msgs_{tab_key}" not in st.session_state: st.session_state[f"msgs_{tab_key}"] = []
    for m in st.session_state[f"msgs_{tab_key}"]:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if not is_premium and daily_questions >= 10:
        st.warning("Bạn đã hết 10 câu hỏi miễn phí hôm nay. Vui lòng nâng cấp Premium để tiếp tục.")
    else:
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
                    
                    if not is_premium:
                        supabase.table("users").update({"daily_questions": daily_questions + 1}).eq("username", username).execute()
                        st.rerun()

# --- TRANG 2: NHÓM HỌC TẬP ---
elif st.session_state.page == "Nhóm":
    st.header("Nhóm học tập")
    
    with st.expander("Tạo nhóm mới"):
        with st.form("create_group_form"):
            group_name = st.text_input("Tên nhóm")
            if is_admin:
                group_type = st.selectbox("Loại nhóm", ["Cộng đồng (Chỉ Admin)", "Học tập (Mọi người)", "Bạn bè (Mọi người)"])
                type_val = "community" if "Cộng đồng" in group_type else ("friends" if "Bạn bè" in group_type else "study")
            else:
                group_type = st.selectbox("Loại nhóm", ["Học tập", "Bạn bè"])
                type_val = "friends" if "Bạn bè" in group_type else "study"
                
            submit_group = st.form_submit_button("Tạo nhóm", type="primary")
            if submit_group and group_name.strip():
                try:
                    supabase.table("groups").insert({"group_name": group_name, "group_type": type_val, "created_by": username}).execute()
                    st.success("Đã tạo nhóm thành công!")
                    time.sleep(1)
                    st.rerun()
                except Exception: 
                    st.error("Lỗi: Tên nhóm này đã tồn tại.")
                
    st.divider()
    try:
        groups = supabase.table("groups").select("*").order("created_at", desc=True).execute()
        if not groups.data:
            st.info("Chưa có nhóm nào. Hãy tạo nhóm đầu tiên!")
        else:
            for g in groups.data:
                with st.container(border=True):
                    col_info, col_btn = st.columns([4, 1])
                    with col_info:
                        # Sử dụng nhãn chữ thay vì emoji
                        label = "[Cộng đồng]" if g['group_type'] == 'community' else ("[Bạn bè]" if g['group_type'] == 'friends' else "[Học tập]")
                        st.markdown(f"### {label} {g['group_name']}")
                        st.caption(f"Loại: **{g['group_type'].capitalize()}** | Tạo bởi: **{g['created_by']}**")
                    with col_btn:
                        st.button("Tham gia", key=f"join_group_{g['id']}", use_container_width=True)
    except: pass

# --- TRANG 3: GIẢI BÀI QUA ẢNH ---
elif st.session_state.page == "Giải bài qua ảnh":
    st.header("Giải bài tập qua ảnh")
    img_source = st.radio("Nguồn ảnh:", ["Tải ảnh từ máy", "Chụp ảnh bằng Camera"], horizontal=True, index=0)
    image_data = st.file_uploader("Tải ảnh", type=["jpg", "png"]) if img_source == "Tải ảnh từ máy" else st.camera_input("Chụp ảnh")
    
    if image_data:
        img = Image.open(image_data)
        st.image(img, width=250)
        with st.spinner("Đang phân tích..."):
            model = genai.GenerativeModel('gemini-3.5-flash-lite') 
            res = model.generate_content(["Hãy giải chi tiết bài tập trong ảnh.", img])
            st.markdown("### Kết quả:")
            st.markdown(res.text)

# --- TRANG 4: PHÒNG HỌC NHÓM ---
elif st.session_state.page == "Phòng học nhóm":
    st.header("Sảnh phòng học")
    
    if "active_room" in st.session_state and st.session_state.active_room:
        st.subheader(f"Đang trong phòng: {st.session_state.active_room}")
        if st.button("Rời phòng", type="primary"):
            st.session_state.active_room = None
            st.rerun()
            
        components.html(f"""
        <div id="jitsi-container" style="width: 100%; height: 500px;"></div>
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
                new_room_name = st.text_input("Tên phòng")
                room_password = st.text_input("Mật khẩu (Nếu muốn để riêng tư)", type="password", help="Để trống nếu muốn phòng công khai")
                submit_room = st.form_submit_button("Tạo phòng", type="primary")
                if submit_room and new_room_name.strip():
                    try:
                        supabase.table("study_rooms").insert({"room_name": new_room_name, "is_public": True, "password": room_password, "created_by": username}).execute()
                        st.success("Tạo phòng thành công!")
                        time.sleep(1)
                        st.rerun()
                    except: st.error("Lỗi: Tên phòng đã tồn tại.")
                        
        with col_list:
            st.subheader("Danh sách phòng (Sảnh chờ)")
            try:
                rooms = supabase.table("study_rooms").select("*").eq("is_public", True).execute()
                if not rooms.data: st.info("Chưa có phòng nào.")
                for room in rooms.data:
                    with st.container(border=True):
                        st.write(f"**{room['room_name']}** (Tạo bởi: {room['created_by']})")
                        
                        if room.get('password'):
                            col_pwd, col_btn = st.columns([2, 1])
                            with col_pwd:
                                pwd_input = st.text_input("Mật khẩu:", type="password", key=f"pwd_{room['id']}", label_visibility="collapsed")
                            with col_btn:
                                if st.button("Tham gia", key=f"join_{room['id']}", use_container_width=True):
                                    if pwd_input == room['password']:
                                        st.session_state.active_room = room['room_name']
                                        st.rerun()
                                    else:
                                        st.error("Sai mật khẩu!")
                        else:
                            st.caption("Phòng công khai")
                            if st.button("Tham gia", key=f"join_{room['id']}"):
                                st.session_state.active_room = room['room_name']
                                st.rerun()
            except: pass

# --- TRANG 5: DIỄN ĐÀN ---
elif st.session_state.page == "Diễn đàn":
    st.header("Diễn đàn học tập")
    
    with st.expander("Đăng bài viết mới"):
        title = st.text_input("Tiêu đề")
        content = st.text_area("Nội dung")
        tags_input = st.text_input("Hashtag (VD: toan12, onthi)")
        uploaded_img = st.file_uploader("Đính kèm ảnh", type=["jpg", "png"])
        
        if st.button("Đăng bài", type="primary"):
            if title and content:
                image_url = None
                if uploaded_img:
                    f_bytes = uploaded_img.read()
                    f_name = f"forum_{username}_{int(time.time())}.png"
                    supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                    image_url = supabase.storage.from_("public_images").get_public_url(f_name)
                supabase.table("forum_posts").insert({"username": username, "title": title, "content": content, "tags": tags_input, "image_url": image_url}).execute()
                st.success("Đăng bài thành công!"); time.sleep(1); st.rerun()
                
    st.divider()
    
    try:
        posts = supabase.table("forum_posts").select("*").order("created_at", desc=True).execute()
        for post in posts.data:
            with st.container(border=True):
                col_title, col_del = st.columns([8, 1])
                with col_title: st.markdown(f"### {post['title']}")
                with col_del:
                    if post['username'] == username or is_admin:
                        if st.button("Xóa", key=f"del_post_{post['id']}"):
                            supabase.table("forum_posts").delete().eq("id", post['id']).execute()
                            st.rerun()
                            
                st.caption(f"Đăng bởi: **{post['username']}** | {post['created_at'][:10]}")
                st.write(post['content'])
                if post.get('image_url'): st.image(post['image_url'], width=400)
                if post.get('tags'):
                    hashtag_html = "".join([f'<span class="hashtag-pill">#{t.strip()}</span>' for t in post['tags'].split(',') if t.strip()])
                    st.markdown(hashtag_html, unsafe_allow_html=True)
                
                with st.expander("Bình luận"):
                    comments = supabase.table("forum_comments").select("*").eq("post_id", post['id']).order("created_at").execute()
                    for cmt in comments.data:
                        st.markdown(f"**{cmt['username']}**: {cmt['comment']}")
                        
                    new_cmt = st.text_input("Viết bình luận...", key=f"cmt_{post['id']}")
                    if st.button("Gửi", key=f"send_{post['id']}"):
                        if new_cmt:
                            supabase.table("forum_comments").insert({"post_id": post['id'], "username": username, "comment": new_cmt}).execute()
                            st.rerun()
    except: pass

# --- TRANG 6: HỒ SƠ ---
elif st.session_state.page == "Hồ sơ":
    if not st.session_state.get("edit_profile", False):
        banner_url = user_info.get("banner_url")
        if banner_url:
            st.image(banner_url, use_column_width=True)
        else:
            st.markdown("<div style='height: 150px; background: linear-gradient(to right, #CBA6F7, #89B4FA); border-radius: 10px;'></div>", unsafe_allow_html=True)
            
        col1, col2 = st.columns([1, 3])
        with col1:
            avt = user_info.get("avatar_url") or "https://api.dicebear.com/7.x/avataaars/svg?seed=" + username
            st.image(avt, use_column_width=True)
        with col2:
            st.title(user_info.get("display_name") or username)
            st.markdown(f"**Streak:** {user_info.get('streak_count', 1)} ngày | **Tham gia:** {user_info.get('created_at', '')[:10]}")
            if st.button("Chỉnh sửa hồ sơ"):
                st.session_state.edit_profile = True
                st.rerun()
            st.divider()
            st.write(f"**Bio:** {user_info.get('bio') or 'Chưa có thông tin.'}")
    else:
        st.subheader("Chỉnh sửa Hồ sơ")
        new_name = st.text_input("Tên hiển thị", value=user_info.get("display_name") or username)
        
        col_avt, col_banner = st.columns(2)
        with col_avt:
            avt_file = st.file_uploader("Ảnh đại diện (Avatar)", type=["jpg", "png"])
        with col_banner:
            banner_file = st.file_uploader("Ảnh bìa (Banner - Hỗ trợ GIF)", type=["jpg", "png", "gif"])
            
        new_bio = st.text_area("Giới thiệu", value=user_info.get("bio") or "")
        
        col_s, col_c = st.columns(2)
        with col_s:
            if st.button("Lưu thay đổi", type="primary", use_container_width=True):
                upd = {"display_name": new_name, "bio": new_bio}
                if avt_file:
                    f_bytes = avt_file.read()
                    f_name = f"avt_{username}_{int(time.time())}.png"
                    supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                    upd["avatar_url"] = supabase.storage.from_("public_images").get_public_url(f_name)
                if banner_file:
                    f_bytes = banner_file.read()
                    f_name = f"banner_{username}_{int(time.time())}.{banner_file.name.split('.')[-1]}"
                    supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                    upd["banner_url"] = supabase.storage.from_("public_images").get_public_url(f_name)
                    
                supabase.table("users").update(upd).eq("username", username).execute()
                st.success("Đã lưu!"); st.session_state.edit_profile = False; time.sleep(1); st.rerun()
        with col_c:
            if st.button("Hủy", use_container_width=True):
                st.session_state.edit_profile = False
                st.rerun()
