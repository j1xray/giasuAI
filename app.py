import streamlit as st
import os
import time
import base64
import requests
from datetime import datetime, timedelta, timezone
from PIL import Image
import google.generativeai as genai
from supabase import create_client
import streamlit.components.v1 as components
import random

# ===== 1. CẤU HÌNH TRANG & CSS (GIAO DIỆN CHATGPT) =====
st.set_page_config(page_title="Gia Sư AI", page_icon="🧠", layout="wide")

custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Font chữ toàn app */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* Ẩn thanh header mặc định của Streamlit */
header {visibility: hidden;}

/* Nền tối cho toàn bộ trang */
.stApp {
    background-color: #212121; 
}

/* Thiết kế Khung Đăng Nhập */
.login-container {
    background-color: #2f2f2f;
    padding: 40px;
    border-radius: 16px;
    width: 100%;
    max-width: 420px;
    margin: 80px auto;
    text-align: center;
    box-shadow: 0 10px 40px rgba(0,0,0,0.4);
    border: 1px solid #444;
}
.login-title {
    color: white;
    font-size: 28px;
    font-weight: 600;
    margin-bottom: 10px;
}
.login-subtitle {
    color: #b4b4b4;
    font-size: 14px;
    margin-bottom: 30px;
    line-height: 1.5;
}
.divider {
    display: flex;
    align-items: center;
    text-align: center;
    color: #888;
    margin: 25px 0;
    font-size: 12px;
    font-weight: 600;
}
.divider::before, .divider::after {
    content: '';
    flex: 1;
    border-bottom: 1px solid #555;
}
.divider::before { margin-right: 15px; }
.divider::after { margin-left: 15px; }

/* Tùy chỉnh nút bấm */
div.stButton > button {
    width: 100%;
    background-color: #2f2f2f;
    color: white;
    border: 1px solid #555;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 15px;
    font-weight: 500;
    transition: all 0.2s ease;
}
div.stButton > button:hover {
    background-color: #3f3f3f;
    border-color: #777;
    color: white;
}

/* Nút Continue màu trắng */
div.stButton > button[kind="primary"] {
    background-color: white;
    color: black;
    border: none;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #e0e0e0;
    color: black;
}

/* Tùy chỉnh ô nhập liệu */
div[data-testid="stTextInput"] input {
    background-color: #212121 !important;
    color: white !important;
    border: 1px solid #555 !important;
    border-radius: 8px !important;
    padding: 12px !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #888 !important;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ===== 2. KHỞI TẠO KẾT NỐI =====
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error(f"❌ Lỗi cấu hình: {e}")
    st.stop()

# ===== 3. FORM ĐĂNG NHẬP =====
if not st.user.is_logged_in and "guest_user" not in st.session_state:
    
    st.markdown("""
    <div class="login-container">
        <div class="login-title">Log in or sign up</div>
        <div class="login-subtitle">Bạn sẽ có trải nghiệm học tập tốt hơn,<br>có thể lưu lịch sử chat và tải file lên.</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        # Nút Google
        if st.button("🌐 Continue with Google", use_container_width=True):
            try:
                st.login("google")
            except Exception as e:
                st.warning("Chức năng đăng nhập Google đang bảo trì, vui lòng dùng tài khoản Khách bên dưới.")
        
        st.markdown('<div class="divider">OR</div>', unsafe_allow_html=True)
        
        # Ô nhập tên Khách
        guest_name = st.text_input("Tên của bạn", placeholder="Nhập tên của bạn (VD: nghia123)", label_visibility="collapsed")
        
        # Nút Continue (Guest)
        if st.button("Continue as Guest", use_container_width=True, type="primary"):
            if guest_name.strip():
                st.session_state.guest_user = guest_name.strip()
            else:
                st.session_state.guest_user = f"Guest_{random.randint(1000, 9999)}"
            st.rerun()
    st.stop()

# ===== 4. XÁC ĐỊNH USER =====
if "guest_user" in st.session_state:
    username = st.session_state.guest_user
    is_admin = False
    user_avatar = "👤"
else:
    username = st.user.email.split('@')[0]
    is_admin = (st.user.email == "email_admin_cua_ban@gmail.com") # Sửa email admin thật của bạn
    user_avatar = st.user.picture

# Lưu user vào DB nếu chưa có
try:
    user_check = supabase.table("users").select("*").eq("username", username).execute()
    if not user_check.data:
        supabase.table("users").insert({"username": username, "password": "oauth_user"}).execute()
except: pass

# ===== 5. QUẢN LÝ GÓI DỊCH VỤ =====
now = datetime.now(timezone.utc)
is_premium = False
try:
    res = supabase.table("user_subscriptions").select("*").eq("username", username).execute()
    if len(res.data) == 0:
        trial_end = now + timedelta(days=7)
        supabase.table("user_subscriptions").insert({"username": username, "expiry_date": trial_end.isoformat()}).execute()
        is_premium = True
    else:
        expiry_date = datetime.fromisoformat(res.data[0]["expiry_date"].replace('Z', '+00:00'))
        is_premium = now < expiry_date
except: pass

# ===== 6. SIDEBAR (MENU CHÍNH) =====
with st.sidebar:
    col_avt, col_info = st.columns([1, 3])
    with col_avt:
        if isinstance(user_avatar, str) and user_avatar.startswith("http"):
            st.image(user_avatar, width=50)
        else:
            st.markdown("<h1 style='text-align: center;'>👤</h1>", unsafe_allow_html=True)
    with col_info:
        st.subheader(username)
        st.caption("Quản trị viên" if is_admin else "Học viên")
    
    st.divider()
    
    st.subheader("👥 Nhóm học tập")
    with st.expander("➕ Tạo nhóm mới"):
        group_name = st.text_input("Tên nhóm")
        if is_admin:
            group_type = st.selectbox("Loại nhóm", ["Cộng đồng (Community)", "Học tập (Study)"])
            type_val = "community" if "Cộng đồng" in group_type else "study"
        else:
            st.info("Chỉ Admin mới có thể tạo nhóm cộng đồng.")
            type_val = "study"
            
        if st.button("Tạo nhóm", use_container_width=True):
            try:
                supabase.table("groups").insert({"group_name": group_name, "group_type": type_val, "created_by": username}).execute()
                st.toast("✅ Đã tạo nhóm thành công!")
            except Exception as e: 
                st.toast("❌ Lỗi: Tên nhóm có thể đã tồn tại", icon="❌")
            
    if st.button("Đăng xuất", use_container_width=True):
        if "guest_user" in st.session_state:
            del st.session_state.guest_user
        if st.user.is_logged_in:
            st.logout()
        st.rerun()

# ===== 7. CÁC TABS CHÍNH =====
tab_chat, tab_room, tab_social, tab_forum = st.tabs(["💬 Chat AI", "🎥 Phòng Học", "👫 Bạn Bè", "📚 Diễn Đàn"])

# --- TAB CHAT AI ---
with tab_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Chào bạn! Mình có thể giúp gì hôm nay?"}]
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
    if prompt := st.chat_input("Hỏi bài..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel('gemini-3.6-flash')
                res = model.generate_content(prompt)
                st.markdown(res.text)
                st.session_state.messages.append({"role": "assistant", "content": res.text})
            except Exception as e:
                st.toast(f"Lỗi AI: {e}", icon="❌")

# --- TAB PHÒNG HỌC ---
with tab_room:
    st.subheader("Phòng Học Nhóm")
    
    with st.expander("➕ Tạo phòng học mới"):
        new_room = st.text_input("Tên phòng (VD: onthi_toan12)")
        room_topic = st.text_input("Chủ đề (VD: Ôn thi giữa kỳ)")
        is_public = st.checkbox("Phòng công khai", value=True)
        if st.button("Tạo phòng"):
            try:
                supabase.table("study_rooms").insert({
                    "room_name": new_room, "topic": room_topic, 
                    "is_public": is_public, "created_by": username
                }).execute()
                st.toast("✅ Tạo phòng thành công!")
                time.sleep(1)
                st.rerun()
            except: st.toast("❌ Lỗi: Tên phòng đã tồn tại.", icon="❌")
            
    st.divider()
    
    st.write("### Các phòng công khai đang mở:")
    try:
        rooms = supabase.table("study_rooms").select("*").eq("is_public", True).execute()
        if not rooms.data:
            st.info("Chưa có phòng công khai nào.")
        else:
            room_names = [r["room_name"] for r in rooms.data]
            selected_room = st.selectbox("Chọn phòng để tham gia:", room_names)
            
            if selected_room and st.button("Vào phòng"):
                jitsi_html = f"""
                <div id="jitsi-container" style="width: 100%; height: 500px;"></div>
                <script src="https://meet.jit.si/external_api.js"></script>
                <script>
                    const api = new JitsiMeetExternalAPI("meet.jit.si", {{
                        roomName: "{selected_room}",
                        parentNode: document.querySelector('#jitsi-container'),
                        width: "100%", height: 500,
                        userInfo: {{ displayName: "{username}" }}
                    }});
                </script>
                """
                components.html(jitsi_html, height=520)
    except Exception as e:
        st.error(f"Lỗi tải danh sách phòng: {e}")

# --- TAB BẠN BÈ ---
with tab_social:
    st.subheader("Kết Nối Bạn Bè")
    
    friend_name = st.text_input("Nhập tên người dùng để kết bạn:")
    if st.button("Gửi lời mời"):
        if friend_name == username: st.warning("Không thể tự kết bạn với chính mình!")
        else:
            try:
                supabase.table("friendships").insert({"sender": username, "receiver": friend_name}).execute()
                st.toast("✅ Đã gửi lời mời kết bạn!")
            except: st.toast("Đã có lỗi xảy ra.", icon="❌")
            
    st.divider()
    
    st.write("### Lời mời kết bạn đang chờ:")
    try:
        requests = supabase.table("friendships").select("*").eq("receiver", username).eq("status", "pending").execute()
        if not requests.data:
            st.write("Không có lời mời nào.")
        else:
            for req in requests.data:
                col1, col2 = st.columns([3, 1])
                with col1: st.write(f"**{req['sender']}** muốn kết bạn với bạn.")
                with col2:
                    if st.button("Chấp nhận", key=f"acc_{req['id']}"):
                        supabase.table("friendships").update({"status": "accepted"}).eq("id", req['id']).execute()
                        st.rerun()
    except Exception as e:
        st.info("Hệ thống kết bạn đang được bảo trì.")

# --- TAB DIỄN ĐÀN ---
with tab_forum:
    st.subheader("Diễn Đàn Học Tập")
    
    with st.expander("➕ Đăng bài thảo luận"):
        title = st.text_input("Tiêu đề")
        content = st.text_area("Nội dung")
        if st.button("Đăng bài"):
            try:
                supabase.table("forum_posts").insert({"username": username, "title": title, "content": content}).execute()
                st.rerun()
            except: st.toast("Lỗi đăng bài!", icon="❌")
            
    try:
        posts = supabase.table("forum_posts").select("*").order("created_at", desc=True).execute()
        for post in posts.data:
            with st.container(border=True):
                st.markdown(f"### {post['title']}")
                st.caption(f"Đăng bởi: {post['username']}")
                st.write(post['content'])
    except: pass
