import streamlit as st
import time
from PIL import Image
import google.generativeai as genai
import streamlit.components.v1 as components

def render_ai(supabase, math_brain, code_brain, username, is_premium, daily_questions):
    st.header("Trợ lý AI")
    ai_type = st.selectbox("Chọn chế độ", ["Gia sư Toán", "Kỹ sư Code"])
    agent = math_brain if ai_type == "Gia sư Toán" else code_brain
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

def render_groups(supabase, username, is_admin):
    st.header("Nhóm học tập")
    with st.expander("Tạo nhóm mới"):
        with st.form("create_group_form"):
            group_name = st.text_input("Tên nhóm")
            if is_admin:
                group_type = st.selectbox("Loại nhóm", ["Cộng đồng", "Học tập", "Bạn bè"])
                type_val = "community" if group_type == "Cộng đồng" else ("friends" if group_type == "Bạn bè" else "study")
            else:
                group_type = st.selectbox("Loại nhóm", ["Học tập", "Bạn bè"])
                type_val = "friends" if group_type == "Bạn bè" else "study"
            if st.form_submit_button("Tạo nhóm", type="primary") and group_name.strip():
                try:
                    supabase.table("groups").insert({"group_name": group_name, "group_type": type_val, "created_by": username}).execute()
                    st.success("Đã tạo nhóm thành công!"); time.sleep(1); st.rerun()
                except: st.error("Lỗi: Tên nhóm đã tồn tại.")
    st.divider()
    try:
        groups = supabase.table("groups").select("*").order("created_at", desc=True).execute()
        for g in groups.data:
            with st.container(border=True):
                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    label = "[Cộng đồng]" if g['group_type'] == 'community' else ("[Bạn bè]" if g['group_type'] == 'friends' else "[Học tập]")
                    st.markdown(f"### {label} {g['group_name']}")
                    st.caption(f"Tạo bởi: **{g['created_by']}**")
                with col_btn:
                    st.button("Tham gia", key=f"join_group_{g['id']}", use_container_width=True)
    except: pass

def render_image_solver():
    st.header("Giải bài tập qua ảnh")
    img_source = st.radio("Nguồn ảnh:", ["Tải ảnh từ máy", "Chụp ảnh bằng Camera"], horizontal=True, index=0)
    image_data = st.file_uploader("Tải ảnh", type=["jpg", "png"]) if img_source == "Tải ảnh từ máy" else st.camera_input("Chụp ảnh")
    if image_data:
        img = Image.open(image_data)
        st.image(img, width=250)
        with st.spinner("Đang phân tích..."):
            model = genai.GenerativeModel('gemini-3.5-flash-lite') 
            res = model.generate_content(["Hãy giải chi tiết bài tập trong ảnh.", img])
            st.markdown("### Kết quả:"); st.markdown(res.text)

def render_rooms(supabase, username):
    st.header("Sảnh phòng học")
    if "active_room" in st.session_state and st.session_state.active_room:
        st.subheader(f"Đang trong phòng: {st.session_state.active_room}")
        if st.button("Rời phòng", type="primary"):
            st.session_state.active_room = None; st.rerun()
        components.html(f"""
        <div id="jitsi-container" style="width: 100%; height: 500px;"></div>
        <script src="https://meet.jit.si/external_api.js"></script>
        <script>
            new JitsiMeetExternalAPI("meet.jit.si", {{ roomName: "{st.session_state.active_room}", parentNode: document.querySelector('#jitsi-container'), width: "100%", height: 500, userInfo: {{ displayName: "{username}" }} }});
        </script>
        """, height=520)
    else:
        col_create, col_list = st.columns([1, 2])
        with col_create:
            st.subheader("Tạo phòng mới")
            with st.form("create_room_form"):
                new_room_name = st.text_input("Tên phòng")
                room_password = st.text_input("Mật khẩu (Để trống nếu công khai)", type="password")
                if st.form_submit_button("Tạo phòng", type="primary") and new_room_name.strip():
                    try:
                        supabase.table("study_rooms").insert({"room_name": new_room_name, "is_public": True, "password": room_password, "created_by": username}).execute()
                        st.success("Tạo phòng thành công!"); time.sleep(1); st.rerun()
                    except: st.error("Lỗi: Tên phòng đã tồn tại.")
        with col_list:
            st.subheader("Danh sách phòng")
            try:
                rooms = supabase.table("study_rooms").select("*").eq("is_public", True).execute()
                for room in rooms.data:
                    with st.container(border=True):
                        st.write(f"**{room['room_name']}** (Tạo bởi: {room['created_by']})")
                        if room.get('password'):
                            col_pwd, col_btn = st.columns([2, 1])
                            with col_pwd: pwd_input = st.text_input("Mật khẩu:", type="password", key=f"pwd_{room['id']}", label_visibility="collapsed")
                            with col_btn:
                                if st.button("Tham gia", key=f"join_{room['id']}", use_container_width=True):
                                    if pwd_input == room['password']: st.session_state.active_room = room['room_name']; st.rerun()
                                    else: st.error("Sai mật khẩu!")
                        else:
                            if st.button("Tham gia", key=f"join_{room['id']}"):
                                st.session_state.active_room = room['room_name']; st.rerun()
            except: pass

def render_forum(supabase, username, is_admin):
    st.header("Diễn đàn học tập")
    with st.expander("Đăng bài viết mới"):
        title = st.text_input("Tiêu đề")
        content = st.text_area("Nội dung")
        tags_input = st.text_input("Hashtag (VD: toan12, onthi)")
        uploaded_img = st.file_uploader("Đính kèm ảnh", type=["jpg", "png"])
        if st.button("Đăng bài", type="primary") and title and content:
            image_url = None
            if uploaded_img:
                f_bytes = uploaded_img.read(); f_name = f"forum_{username}_{int(time.time())}.png"
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
                            supabase.table("forum_posts").delete().eq("id", post['id']).execute(); st.rerun()
                st.caption(f"Đăng bởi: **{post['username']}** | {post['created_at'][:10]}")
                st.write(post['content'])
                if post.get('image_url'): st.image(post['image_url'], width=400)
                if post.get('tags'):
                    hashtag_html = "".join([f'<span class="hashtag-pill">#{t.strip()}</span>' for t in post['tags'].split(',') if t.strip()])
                    st.markdown(hashtag_html, unsafe_allow_html=True)
                with st.expander("Bình luận"):
                    comments = supabase.table("forum_comments").select("*").eq("post_id", post['id']).order("created_at").execute()
                    for cmt in comments.data: st.markdown(f"**{cmt['username']}**: {cmt['comment']}")
                    new_cmt = st.text_input("Viết bình luận...", key=f"cmt_{post['id']}")
                    if st.button("Gửi", key=f"send_{post['id']}") and new_cmt:
                        supabase.table("forum_comments").insert({"post_id": post['id'], "username": username, "comment": new_cmt}).execute(); st.rerun()
    except: pass

def render_profile(supabase, user_info, username):
    if not st.session_state.get("edit_profile", False):
        banner_url = user_info.get("banner_url") or "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?q=80&w=2070&auto=format&fit=crop"
        avt_url = user_info.get("avatar_url") or "https://api.dicebear.com/7.x/avataaars/svg?seed=" + username
        st.markdown(f"""
        <div style="position: relative; margin-bottom: 70px;">
            <div style="width: 100%; height: 220px; background-image: url('{banner_url}'); background-size: cover; background-position: center; border-radius: 12px; background-color: #313244;"></div>
            <div style="position: absolute; bottom: -50px; left: 30px;">
                <img src="{avt_url}" style="width: 120px; height: 120px; border-radius: 50%; border: 6px solid #1E1E2E; object-fit: cover;">
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col_info, col_edit = st.columns([3, 1])
        with col_info:
            st.markdown(f"""
            <div style="padding-left: 30px;">
                <h1 style="color: #89B4FA; margin: 0; font-size: 32px;">{user_info.get('display_name') or username}</h1>
                <span style="color: #A6ADC8; font-size: 15px;">@{username}</span>
                <br><br>
                <span style="color: #A6ADC8; font-size: 14px;">Streak: {user_info.get('streak_count', 1)} ngày | Tham gia: {user_info.get('created_at', '')[:10]}</span>
            </div>
            """, unsafe_allow_html=True)
        with col_edit:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("Chỉnh sửa hồ sơ", key="btn_edit_profile", use_container_width=True):
                st.session_state.edit_profile = True; st.rerun()
        st.markdown("<hr style='border-color: #313244; margin: 20px 0;'>", unsafe_allow_html=True)
        st.markdown(f"**Ngày sinh:** {user_info.get('birth_date') or 'Chưa cập nhật'}")
        st.markdown(f"**Giới tính:** {user_info.get('gender') or 'Chưa cập nhật'}")
        st.markdown(f"**Giới thiệu:** {user_info.get('bio') or 'Chưa có thông tin.'}")
    else:
        st.subheader("Chỉnh sửa Hồ sơ")
        new_name = st.text_input("Tên hiển thị", value=user_info.get("display_name") or username)
        col_avt, col_banner = st.columns(2)
        with col_avt: avt_file = st.file_uploader("Ảnh đại diện (Avatar)", type=["jpg", "png"])
        with col_banner: banner_file = st.file_uploader("Ảnh bìa (Banner - Hỗ trợ GIF)", type=["jpg", "png", "gif"])
        new_bio = st.text_area("Giới thiệu", value=user_info.get("bio") or "")
        
        col_s, col_c = st.columns(2)
        with col_s:
            if st.button("Lưu thay đổi", type="primary", use_container_width=True):
                upd = {"display_name": new_name, "bio": new_bio}
                if avt_file:
                    f_bytes = avt_file.read(); f_name = f"avt_{username}_{int(time.time())}.png"
                    supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                    upd["avatar_url"] = supabase.storage.from_("public_images").get_public_url(f_name)
                if banner_file:
                    f_bytes = banner_file.read(); f_name = f"banner_{username}_{int(time.time())}.{banner_file.name.split('.')[-1]}"
                    supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                    upd["banner_url"] = supabase.storage.from_("public_images").get_public_url(f_name)
                supabase.table("users").update(upd).eq("username", username).execute()
                st.success("Đã lưu!"); st.session_state.edit_profile = False; time.sleep(1); st.rerun()
        with col_c:
            if st.button("Hủy", use_container_width=True):
                st.session_state.edit_profile = False; st.rerun()

import streamlit as st

def load_css():
    custom_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #1E1E2E; color: #CDD6F4; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}

    [data-testid="stSidebar"] { background-color: #181825; border-right: 1px solid #313244; padding-top: 15px;}
    [data-testid="stSidebar"] div.stButton > button {
        background-color: transparent !important; border: none !important; text-align: left !important;
        justify-content: flex-start !important; padding: 10px 15px !important; font-size: 16px !important;
        font-weight: 600 !important; color: #CDD6F4 !important; border-radius: 10px !important;
        transition: background-color 0.2s ease !important; margin-bottom: 2px; display: flex !important; align-items: center !important;
    }
    [data-testid="stSidebar"] div.stButton > button:hover { background-color: #313244 !important; color: #CBA6F7 !important; }

    .profile-container { display: flex; align-items: center; gap: 12px; padding: 0px 15px; margin-bottom: 20px; }
    .profile-avatar { width: 50px; height: 50px; border-radius: 50%; object-fit: cover; border: 2px solid #CBA6F7; }
    .profile-name { font-weight: 600; font-size: 15px; color: #CDD6F4; line-height: 1.2; }
    .profile-username { font-size: 13px; color: #A6ADC8; }

    .st-key-btn_edit_profile button {
        background-color: transparent !important; color: #CDD6F4 !important; border: 1px solid #585B70 !important;
        border-radius: 20px !important; font-size: 14px !important; padding: 5px 15px !important;
        font-weight: 600 !important; transition: all 0.2s ease !important;
    }
    .st-key-btn_edit_profile button:hover { background-color: #313244 !important; border-color: #CBA6F7 !important; color: #CBA6F7 !important; }

    div.stButton > button[kind="primary"] { background-color: #CBA6F7; color: #11111B; border: none; font-weight: 600; }
    div.stButton > button[kind="primary"]:hover { background-color: #F5C2E7; }

    div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea { 
        background-color: #181825 !important; color: #CDD6F4 !important; border: 1px solid #45475A !important; border-radius: 8px !important; 
    }

    .hashtag-pill {
        display: inline-block; background-color: #313244; color: #89B4FA; padding: 4px 12px; 
        border-radius: 16px; font-size: 13px; font-weight: 600; margin-right: 6px; margin-top: 8px; border: 1px solid #45475A;
    }

    /* NHÓM 3: CSS CHO ĐIỆN THOẠI (MOBILE) */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] { display: none; } /* Ẩn sidebar trên mobile */
        .block-container { padding: 1rem !important; }
        h1 { font-size: 24px !important; }
        h2 { font-size: 20px !important; }
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def render_sidebar(user_info, username, is_admin):
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
        
        st.markdown("<hr style='border-color: #313244; margin: 10px 15px;'>", unsafe_allow_html=True)
        
        if "page" not in st.session_state: st.session_state.page = "Trợ lý AI"
        
        if st.button("🏠 Trang chủ (Trợ lý AI)", use_container_width=True): st.session_state.page = "Trợ lý AI"; st.rerun()
        if st.button("👥 Nhóm học tập", use_container_width=True): st.session_state.page = "Nhóm"; st.rerun()
        if st.button("📸 Giải bài qua ảnh", use_container_width=True): st.session_state.page = "Giải bài qua ảnh"; st.rerun()
        if st.button("🎥 Phòng học nhóm", use_container_width=True): st.session_state.page = "Phòng học nhóm"; st.rerun()
        if st.button("📚 Diễn đàn", use_container_width=True): st.session_state.page = "Diễn đàn"; st.rerun()
        if st.button("👤 Hồ sơ", use_container_width=True): st.session_state.page = "Hồ sơ"; st.rerun()
        
        # NHÓM 2: NÚT ADMIN (Chỉ hiện với Admin)
        if is_admin:
            if st.button("👑 Trang Quản Trị", use_container_width=True): st.session_state.page = "Admin"; st.rerun()
            
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # NHÓM 3: PHÁP LÝ
        with st.expander("📜 Điều khoản & Bảo mật"):
            st.markdown("""
            <div style='font-size:12px; color:#A6ADC8;'>
            <b>Điều khoản:</b> Ứng dụng hỗ trợ học tập. Nghiêm cấm dùng để gian lận thi cử.<br><br>
            <b>Bảo mật:</b> Chúng tôi cam kết bảo vệ dữ liệu theo Nghị định 13/2023/NĐ-CP.
            </div>
            """, unsafe_allow_html=True)
            
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.clear()
            if st.user.is_logged_in: st.logout()
            st.rerun()
