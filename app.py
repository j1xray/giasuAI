import streamlit as st
import os
import time
import base64
import requests
from datetime import datetime, timedelta, timezone
from PIL import Image
import google.generativeai as genai
from supabase import create_client
from openai import OpenAI
import streamlit.components.v1 as components
import random
import re

# ===== 1. CẤU HÌNH TRANG & CSS =====
st.set_page_config(page_title="Gia Sư AI", page_icon="🧠", layout="wide")

custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
header {visibility: hidden;}
.stApp { background-color: #212121; }
.login-container {
    background-color: #2f2f2f; padding: 40px; border-radius: 16px;
    width: 100%; max-width: 420px; margin: 80px auto; text-align: center;
    box-shadow: 0 10px 40px rgba(0,0,0,0.4); border: 1px solid #444;
}
.login-title { color: white; font-size: 28px; font-weight: 600; margin-bottom: 10px; }
.login-subtitle { color: #b4b4b4; font-size: 14px; margin-bottom: 30px; line-height: 1.5; }
.divider { display: flex; align-items: center; text-align: center; color: #888; margin: 25px 0; font-size: 12px; font-weight: 600; }
.divider::before, .divider::after { content: ''; flex: 1; border-bottom: 1px solid #555; }
.divider::before { margin-right: 15px; } .divider::after { margin-left: 15px; }
div.stButton > button {
    width: 100%; background-color: #2f2f2f; color: white; border: 1px solid #555;
    border-radius: 8px; padding: 10px 16px; font-size: 15px; font-weight: 500; transition: all 0.2s ease;
}
div.stButton > button:hover { background-color: #3f3f3f; border-color: #777; color: white; }
div.stButton > button[kind="primary"] { background-color: white; color: black; border: none; }
div.stButton > button[kind="primary"]:hover { background-color: #e0e0e0; color: black; }
div[data-testid="stTextInput"] input { background-color: #212121 !important; color: white !important; border: 1px solid #555 !important; border-radius: 8px !important; padding: 12px !important; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ===== 2. KHỞI TẠO KẾT NỐI =====
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error(f"❌ Lỗi cấu hình Secrets: {e}")
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
        if st.button("🌐 Continue with Google", use_container_width=True):
            try: st.login("google")
            except Exception as e: st.error(f"Lỗi Google Auth: {e}")
        
        st.markdown('<div class="divider">OR</div>', unsafe_allow_html=True)
        guest_name = st.text_input("Tên của bạn", placeholder="Nhập tên (VD: nghia123)", label_visibility="collapsed")
        
        if st.button("Continue as Guest", use_container_width=True, type="primary"):
            if guest_name.strip(): st.session_state.guest_user = guest_name.strip()
            else: st.session_state.guest_user = f"Guest_{random.randint(1000, 9999)}"
            st.rerun()
    st.stop()

# ===== 4. XÁC ĐỊNH USER & ADMIN =====
ADMIN_EMAIL = "j1xray0@gmail.com" 

if "guest_user" in st.session_state:
    username = st.session_state.guest_user
    is_admin = False
    user_avatar = "👤"
else:
    username = st.user.email.split('@')[0]
    is_admin = (st.user.email == ADMIN_EMAIL) 
    user_avatar = st.user.picture

# ===== 5. XỬ LÝ STREAK & THÔNG TIN USER =====
now = datetime.now(timezone.utc)
try:
    user_check = supabase.table("users").select("*").eq("username", username).execute()
    if not user_check.data:
        supabase.table("users").insert({
            "username": username, "password": "oauth_user", 
            "last_login": now.isoformat(), "streak_count": 1, "created_at": now.isoformat()
        }).execute()
        user_info = {"streak_count": 1, "created_at": now.isoformat(), "avatar_url": None}
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
except Exception as e:
    pass # Bỏ qua lỗi nếu có để app không sập

# ===== 6. QUẢN LÝ GÓI DỊCH VỤ =====
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

# ===== 7. SIDEBAR =====
with st.sidebar:
    col_avt, col_info = st.columns([1, 3])
    with col_avt:
        avt_url = user_info.get("avatar_url") or user_avatar
        if isinstance(avt_url, str) and avt_url.startswith("http"):
            st.image(avt_url, width=50)
        else:
            st.markdown("<h1 style='text-align: center;'>👤</h1>", unsafe_allow_html=True)
    with col_info:
        display_name = user_info.get("display_name") or username
        st.subheader(display_name)
        st.caption("Admin" if is_admin else "Học viên")
    
    st.divider()
    st.subheader("🤖 Trợ lý AI")
    provider = st.selectbox("Nền tảng", ["Google Gemini", "Groq (Llama 3.3)", "OpenRouter"])
    
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
            try:
                supabase.table("groups").insert({"group_name": group_name, "group_type": type_val, "created_by": username}).execute()
                st.toast("✅ Đã tạo nhóm!")
            except Exception: 
                st.toast("❌ Lỗi: Tên nhóm đã tồn tại", icon="❌")
            
    if st.button("Đăng xuất", use_container_width=True):
        if "guest_user" in st.session_state: del st.session_state.guest_user
        if st.user.is_logged_in: st.logout()
        st.rerun()

# ===== 8. HÀM GỌI AI =====
def get_ai_response(prompt, image=None, provider="Google Gemini"):
    try:
        if provider == "Google Gemini":
            model = genai.GenerativeModel('gemini-3.6-flash')
            content = [prompt]
            if image: content.append(image)
            return model.generate_content(content).text
        elif provider == "Groq (Llama 3.3)":
            if image: return "⚠️ Groq không hỗ trợ đọc ảnh."
            client = OpenAI(api_key=st.secrets["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
            res = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": prompt}])
            return res.choices[0].message.content
        elif provider == "OpenRouter":
            if image: return "⚠️ OpenRouter không hỗ trợ đọc ảnh."
            client = OpenAI(api_key=st.secrets["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
            res = client.chat.completions.create(model="openai/gpt-oss-120b:free", messages=[{"role": "user", "content": prompt}])
            return res.choices[0].message.content
    except Exception as e:
        return f"Lỗi AI: {str(e)}"

# ===== 9. TABS CHÍNH =====
tab_chat, tab_vision, tab_room, tab_social, tab_forum, tab_profile = st.tabs([
    "💬 Chat", "📸 Giải Bài Tập", "🎥 Phòng Học", "👫 Bạn Bè", "📚 Diễn Đàn", "👤 Hồ Sơ"
])

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
            with st.spinner("Đang suy nghĩ..."):
                history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
                res_text = get_ai_response(f"Lịch sử:\n{history_text}\n\nCâu hỏi: {prompt}", provider=provider)
                st.markdown(res_text)
                st.session_state.messages.append({"role": "assistant", "content": res_text})

# --- TAB GIẢI BÀI TẬP QUA ẢNH ---
with tab_vision:
    if not is_premium: st.error("🔒 Tính năng này chỉ dành cho Premium.")
    else:
        img_source = st.radio("Nguồn ảnh:", ["Chụp ảnh", "Tải ảnh lên"], horizontal=True)
        image_data = st.camera_input("Chụp bài tập") if img_source == "Chụp ảnh" else st.file_uploader("Tải ảnh", type=["jpg", "png"])
        if image_data:
            img = Image.open(image_data)
            st.image(img, width=300)
            if st.button("Giải bài này"):
                with st.spinner("Đang phân tích..."):
                    res_text = get_ai_response("Hãy giải chi tiết bài tập trong ảnh.", image=img, provider=provider)
                    st.markdown(res_text)

# --- TAB PHÒNG HỌC ---
with tab_room:
    st.subheader("Phòng Học Nhóm")
    with st.expander("➕ Tạo phòng học mới"):
        new_room = st.text_input("Tên phòng")
        is_public = st.checkbox("Phòng công khai", value=True)
        if st.button("Tạo phòng"):
            try:
                supabase.table("study_rooms").insert({"room_name": new_room, "is_public": is_public, "created_by": username}).execute()
                st.toast("✅ Tạo phòng thành công!"); time.sleep(1); st.rerun()
            except: st.toast("❌ Lỗi: Tên phòng đã tồn tại.", icon="❌")
            
    st.write("### Các phòng đang mở:")
    try:
        rooms = supabase.table("study_rooms").select("*").eq("is_public", True).execute()
        if rooms.data:
            selected_room = st.selectbox("Chọn phòng:", [r["room_name"] for r in rooms.data])
            if selected_room and st.button("Vào phòng"):
                components.html(f"""
                <div id="jitsi-container" style="width: 100%; height: 500px;"></div>
                <script src="https://meet.jit.si/external_api.js"></script>
                <script>
                    const api = new JitsiMeetExternalAPI("meet.jit.si", {{
                        roomName: "{selected_room}", parentNode: document.querySelector('#jitsi-container'),
                        width: "100%", height: 500, userInfo: {{ displayName: "{username}" }}
                    }});
                </script>
                """, height=520)
        else: st.info("Chưa có phòng nào.")
    except: pass

# --- TAB BẠN BÈ ---
with tab_social:
    st.subheader("Kết Nối Bạn Bè")
    friend_name = st.text_input("Nhập tên người dùng để kết bạn:")
    if st.button("Gửi lời mời"):
        if friend_name == username: st.warning("Không thể tự kết bạn!")
        else:
            try:
                supabase.table("friendships").insert({"sender": username, "receiver": friend_name}).execute()
                st.toast("✅ Đã gửi lời mời!")
            except: st.toast("Lỗi gửi lời mời.", icon="❌")
            
    try:
        reqs = supabase.table("friendships").select("*").eq("receiver", username).eq("status", "pending").execute()
        if reqs.data:
            st.write("### Lời mời đang chờ:")
            for req in reqs.data:
                col1, col2 = st.columns([3, 1])
                with col1: st.write(f"**{req['sender']}** muốn kết bạn.")
                with col2:
                    if st.button("Chấp nhận", key=f"acc_{req['id']}"):
                        supabase.table("friendships").update({"status": "accepted"}).eq("id", req['id']).execute()
                        st.rerun()
    except: pass

# --- TAB DIỄN ĐÀN ---
with tab_forum:
    st.subheader("Diễn Đàn Học Tập")
    
    with st.expander("➕ Đăng bài thảo luận"):
        title = st.text_input("Tiêu đề")
        content = st.text_area("Nội dung (Có thể tag @ten_ban_be)")
        uploaded_img = st.file_uploader("Đính kèm ảnh (Tùy chọn)", type=["jpg", "png", "jpeg"])
        
        if st.button("Đăng bài"):
            if not title or not content: st.warning("Vui lòng nhập đủ tiêu đề và nội dung!")
            else:
                bad_words = ["18+", "khiêu dâm", "sex", "nude", "gợi cảm quá mức"]
                if any(word in content.lower() or word in title.lower() for word in bad_words):
                    st.error("🚫 Phát hiện từ khóa 18+. Bài viết bị từ chối!")
                else:
                    image_url = None
                    if uploaded_img:
                        with st.spinner("AI đang kiểm duyệt hình ảnh..."):
                            img = Image.open(uploaded_img)
                            check_res = get_ai_response("Is this image NSFW, sexually explicit, or 18+? Answer only YES or NO.", image=img, provider="Google Gemini")
                            
                            if "YES" in check_res.upper():
                                st.error("🚫 Hình ảnh chứa nội dung 18+. Vui lòng chọn ảnh khác!"); st.stop()
                            else:
                                file_bytes = uploaded_img.read()
                                file_name = f"forum_{username}_{int(time.time())}.png"
                                try:
                                    supabase.storage.from_("public_images").upload(file=file_bytes, path=file_name)
                                    image_url = supabase.storage.from_("public_images").get_public_url(file_name)
                                except Exception as e:
                                    st.error(f"Lỗi upload ảnh: {e}")
                                    
                    if image_url or not uploaded_img:
                        try:
                            supabase.table("forum_posts").insert({
                                "username": username, "title": title, "content": content, "image_url": image_url
                            }).execute()
                            st.toast("✅ Đăng bài thành công!"); time.sleep(1); st.rerun()
                        except: st.toast("Lỗi đăng bài!", icon="❌")
            
    st.divider()
    
    try:
        posts = supabase.table("forum_posts").select("*").order("created_at", desc=True).execute()
        for post in posts.data:
            with st.container(border=True):
                st.markdown(f"### {post['title']}")
                st.caption(f"Đăng bởi: **{post['username']}** | {post['created_at'][:10]}")
                
                display_content = post['content']
                tags = re.findall(r'@(\w+)', display_content)
                for tag in tags: display_content = display_content.replace(f"@{tag}", f"**[@{tag}]**")
                
                st.write(display_content)
                if post.get('image_url'): st.image(post['image_url'], width=400)
    except: pass

# --- TAB HỒ SƠ (GIAO DIỆN ĐÃ GỌN GÀNG) ---
with tab_profile:
    profile_data = supabase.table("users").select("*").eq("username", username).execute().data[0]
    
    join_date_str = profile_data.get("created_at", str(now))[:10]
    join_date = datetime.strptime(join_date_str, "%Y-%m-%d")
    streak = profile_data.get("streak_count", 1)
    
    if "edit_profile" not in st.session_state: st.session_state.edit_profile = False

    if not st.session_state.edit_profile:
        # --- CHẾ ĐỘ XEM HỒ SƠ ---
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 4])
        
        with col1:
            avt = profile_data.get("avatar_url") or user_avatar
            if isinstance(avt, str) and avt.startswith("http"):
                st.image(avt, use_column_width=True)
            else:
                st.markdown("<h1 style='text-align: center; font-size: 80px;'>👤</h1>", unsafe_allow_html=True)
                
        with col2:
            disp_name = profile_data.get("display_name") or username
            
            # Tên và Nút chỉnh sửa nằm ngang hàng
            col_name, col_btn = st.columns([3, 1])
            with col_name:
                st.title(disp_name)
                st.caption(f"Tài khoản: @{username}")
            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True) # Đẩy nút xuống cho thẳng hàng với tên
                if st.button("✏️ Chỉnh sửa", type="primary"):
                    st.session_state.edit_profile = True
                    st.rerun()
            
            st.markdown(f"🔥 **Streak:** `{streak} ngày liên tiếp` &nbsp;|&nbsp; 📅 **Tham gia:** `Tháng {join_date.month}/{join_date.year}`")
            
            st.markdown("---")
            gender = profile_data.get("gender") or "Chưa cập nhật"
            dob_str = profile_data.get("birth_date")
            dob = datetime.strptime(dob_str, "%Y-%m-%d").strftime("%d/%m/%Y") if dob_str else "Chưa cập nhật"
            
            st.write(f"🎂 **Ngày sinh:** {dob}")
            st.write(f"🚻 **Giới tính:** {gender}")
            st.write(f"📝 **Giới thiệu:** {profile_data.get('bio') or 'Chưa có thông tin giới thiệu.'}")
            
    else:
        # --- CHẾ ĐỘ CHỈNH SỬA ---
        st.subheader("✏️ Chỉnh sửa Hồ sơ")
        
        st.write("**1. Ảnh đại diện**")
        avt_file = st.file_uploader("Tải ảnh mới lên", type=["jpg", "png", "jpeg"])
        
        st.write("**2. Thông tin cá nhân**")
        new_name = st.text_input("Tên hiển thị", value=profile_data.get("display_name") or username)
        
        col_dob, col_gender = st.columns(2)
        with col_dob:
            default_dob = datetime.strptime(profile_data.get("birth_date"), "%Y-%m-%d").date() if profile_data.get("birth_date") else datetime(2005, 1, 1).date()
            new_dob = st.date_input("Ngày sinh", value=default_dob, min_value=datetime(1900, 1, 1), max_value=datetime(2026, 12, 31))
        with col_gender:
            gender_options = ["Nam", "Nữ", "Khác"]
            curr_gender = profile_data.get("gender") or "Nam"
            new_gender = st.selectbox("Giới tính", gender_options, index=gender_options.index(curr_gender) if curr_gender in gender_options else 0)
            
        new_bio = st.text_area("Giới thiệu bản thân", value=profile_data.get("bio") or "")
        
        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            if st.button("💾 Lưu thay đổi", type="primary", use_container_width=True):
                with st.spinner("Đang lưu..."):
                    try:
                        update_data = {
                            "display_name": new_name,
                            "birth_date": new_dob.strftime("%Y-%m-%d"),
                            "gender": new_gender,
                            "bio": new_bio
                        }
                        
                        if avt_file:
                            file_bytes = avt_file.read()
                            file_name = f"avt_{username}_{int(time.time())}.png"
                            supabase.storage.from_("public_images").upload(file=file_bytes, path=file_name)
                            new_avt_url = supabase.storage.from_("public_images").get_public_url(file_name)
                            update_data["avatar_url"] = new_avt_url
                            
                        supabase.table("users").update(update_data).eq("username", username).execute()
                        st.toast("✅ Đã lưu hồ sơ thành công!")
                        st.session_state.edit_profile = False
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi lưu: {e}")
        with col_cancel:
            if st.button("❌ Hủy", use_container_width=True):
                st.session_state.edit_profile = False
                st.rerun()
