import streamlit as st
import time
from PIL import Image
import google.generativeai as genai
import streamlit.components.v1 as components
import backend # Import backend

def render_ai(supabase, math_brain, code_brain, username, is_premium, daily_questions):
    st.header("Trợ lý AI")
    
    # Khôi phục lịch sử chat từ DB (FIX LỖI MẤT LỊCH SỬ)
    if "msgs_math" not in st.session_state:
        hist = backend.get_messages(supabase, receiver="AI_MATH")
        st.session_state["msgs_math"] = [{"role": "user" if h['sender']==username else "assistant", "content": h['content']} for h in hist]

    ai_type = st.selectbox("Chọn chế độ", ["Gia sư Toán", "Kỹ sư Code"])
    agent = math_brain if ai_type == "Gia sư Toán" else code_brain
    tab_key = f"msgs_{'math' if ai_type=='Gia sư Toán' else 'code'}"
    
    if tab_key not in st.session_state: st.session_state[tab_key] = []
    for m in st.session_state[tab_key]:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if not is_premium and daily_questions >= 10:
        st.warning("Bạn đã hết 10 câu hỏi miễn phí hôm nay. Vui lòng nâng cấp Premium.")
    else:
        if prompt := st.chat_input(f"Nhập yêu cầu cho {ai_type}..."):
            # Lưu vào DB
            backend.send_message(supabase, username, prompt, receiver="AI_MATH" if ai_type=="Gia sư Toán" else "AI_CODE")
            
            st.session_state[tab_key].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Đang xử lý..."):
                    try:
                        res = agent.invoke({"input": prompt})
                        ans = res["output"]
                    except Exception as e: ans = f"Lỗi: {e}"
                    st.markdown(ans)
                    st.session_state[tab_key].append({"role": "assistant", "content": ans})
                    
                    # Lưu AI trả lời vào DB
                    backend.send_message(supabase, "AI", ans, receiver=username)
                    
                    if not is_premium:
                        supabase.table("users").update({"daily_questions": daily_questions + 1}).eq("username", username).execute()
                        st.rerun()

def render_friends(supabase, username):
    st.header("Bạn Bè & Chat Riêng")
    
    # Tìm kiếm & Kết bạn
    with st.expander("Tìm kiếm và Kết bạn"):
        search_name = st.text_input("Nhập username người muốn kết bạn:")
        if st.button("Gửi lời mời"):
            if search_name and search_name != username:
                try:
                    supabase.table("friendships").insert({"sender": username, "receiver": search_name}).execute()
                    st.success("Đã gửi lời mời!")
                except: st.error("Lỗi hoặc đã gửi rồi.")
                    
    # Lời mời đang chờ
    reqs = supabase.table("friendships").select("*").eq("receiver", username).eq("status", "pending").execute().data
    if reqs:
        st.subheader("Lời mời kết bạn")
        for req in reqs:
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{req['sender']}** muốn kết bạn.")
            if col2.button("Chấp nhận", key=f"acc_{req['id']}"):
                supabase.table("friendships").update({"status": "accepted"}).eq("id", req['id']).execute()
                st.rerun()

    # Danh sách bạn bè & Chat
    st.divider()
    friends = supabase.table("friendships").select("*").eq("status", "accepted").or_(f"sender.eq.{username},receiver.eq.{username}").execute().data
    friend_list = [f['receiver'] if f['sender'] == username else f['sender'] for f in friends]
    
    if friend_list:
        target_friend = st.selectbox("Chọn bạn bè để chat:", friend_list)
        
        # Hiển thị tin nhắn
        messages = backend.get_messages(supabase, receiver=target_friend)
        for m in messages:
            is_me = m['sender'] == username
            with st.chat_message("user" if is_me else "assistant"):
                st.markdown(m['content'])
                if m.get('file_url'):
                    st.image(m['file_url'], width=200) # Nếu là ảnh
                    
        # Gửi tin nhắn
        with st.form("chat_form", clear_on_submit=True):
            msg = st.text_input("Nhập tin nhắn...")
            file = st.file_uploader("Gửi ảnh/file", type=["jpg", "png", "pdf"])
            if st.form_submit_button("Gửi"):
                file_url = None
                if file:
                    # FIX LỖI FILE NẶNG > 2MB
                    if file.size > 2 * 1024 * 1024:
                        st.error("File quá lớn! Vui lòng chọn file dưới 2MB.")
                        st.stop()
                    f_bytes = file.read()
                    f_name = f"chat_{username}_{int(time.time())}_{file.name}"
                    supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                    file_url = supabase.storage.from_("public_images").get_public_url(f_name)
                
                backend.send_message(supabase, username, msg, receiver=target_friend, file_url=file_url)
                st.rerun()
    else:
        st.info("Bạn chưa có người bạn nào. Hãy kết bạn nhé!")

def render_groups(supabase, username, is_admin):
    st.header("Nhóm học tập & Chat nhóm")
    
    # Tạo nhóm
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
    
    # Danh sách nhóm
    groups = supabase.table("groups").select("*").order("created_at", desc=True).execute().data
    if not groups: return
    
    group_dict = {g['group_name']: g['id'] for g in groups}
    selected_group_name = st.selectbox("Chọn nhóm để tham gia/chat", list(group_dict.keys()))
    selected_group_id = group_dict[selected_group_name]
    
    # Kiểm tra xem đã tham gia chưa
    is_member = supabase.table("group_members").select("*").eq("group_id", selected_group_id).eq("username", username).execute().data
    
    if not is_member:
        st.warning("Bạn chưa tham gia nhóm này.")
        # FIX LỖI NÚT THAM GIA
        if st.button("Tham gia nhóm ngay", type="primary"):
            supabase.table("group_members").insert({"group_id": selected_group_id, "username": username}).execute()
            st.success("Đã tham gia nhóm!"); time.sleep(1); st.rerun()
    else:
        st.success(f"Bạn đã là thành viên của nhóm: {selected_group_name}")
        st.divider()
        
        # Chat nhóm
        messages = backend.get_messages(supabase, group_id=selected_group_id)
        for m in messages:
            is_me = m['sender'] == username
            with st.chat_message("user" if is_me else "assistant"):
                st.caption(f"**{m['sender']}**")
                st.markdown(m['content'])
                if m.get('file_url'):
                    st.image(m['file_url'], width=200)
                    
        with st.form("group_chat_form", clear_on_submit=True):
            msg = st.text_input("Nhắn gì đó cho cả nhóm...")
            file = st.file_uploader("Gửi ảnh/file", type=["jpg", "png", "pdf"])
            if st.form_submit_button("Gửi"):
                file_url = None
                if file:
                    if file.size > 2 * 1024 * 1024:
                        st.error("File quá lớn! Tối đa 2MB."); st.stop()
                    f_bytes = file.read()
                    f_name = f"group_{username}_{int(time.time())}_{file.name}"
                    supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                    file_url = supabase.storage.from_("public_images").get_public_url(f_name)
                
                backend.send_message(supabase, username, msg, group_id=selected_group_id, file_url=file_url)
                st.rerun()

# (Các hàm render_image_solver, render_rooms, render_forum giữ nguyên như cũ...)

def render_admin(supabase):
    st.header("👑 Trung Tâm Quản Trị Admin")
    
    tab_stats, tab_users, tab_posts = st.tabs(["Thống kê", "Quản lý User", "Duyệt Bài"])
    
    with tab_stats:
        users = supabase.table("users").select("*").execute().data
        posts = supabase.table("forum_posts").select("*").execute().data
        col1, col2, col3 = st.columns(3)
        col1.metric("Tổng Người Dùng", len(users))
        col2.metric("Người Dùng VIP", len([u for u in users if u.get('is_premium')]))
        col3.metric("Bài Đăng", len(posts))
        
    with tab_users:
        st.subheader("Cấp VIP / Ban User")
        target = st.text_input("Nhập username:")
        c1, c2 = st.columns(2)
        if c1.button("Cấp VIP", type="primary"):
            supabase.table("users").update({"is_premium": True}).eq("username", target).execute()
            st.success(f"Đã nâng VIP cho {target}")
        if c2.button("Thu hồi VIP"):
            supabase.table("users").update({"is_premium": False}).eq("username", target).execute()
            st.success(f"Đã thu hồi VIP của {target}")
            
    with tab_posts:
        posts = supabase.table("forum_posts").select("*").order("created_at", desc=True).execute().data
        for p in posts:
            with st.expander(f"📝 {p['title']} (bởi {p['username']})"):
                st.write(p['content'])
                if st.button("Xóa vĩnh viễn", key=f"admin_del_{p['id']}"):
                    supabase.table("forum_posts").delete().eq("id", p['id']).execute()
                    st.rerun()
