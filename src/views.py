import streamlit as st
import time
import os
from PIL import Image
import google.generativeai as genai
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
import backend

# ==========================================
# 1. GIA SƯ AI (Chat & Lịch sử)
# ==========================================
def render_ai(supabase, math_brain, code_brain, username, is_premium, daily_questions):
    st.header("Trợ lý AI")
    
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
            backend.send_message(supabase, username, prompt, receiver="AI_MATH" if ai_type=="Gia sư Toán" else "AI_CODE")
            st.session_state[tab_key].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Đang xử lý..."):
                    try:
                        res = agent.invoke({"input": prompt})
                        ans = res["output"]
                    except Exception as e: 
                        ans = backend.get_ai_response_fallback(prompt) # Dùng Fallback
                    st.markdown(ans)
                    st.session_state[tab_key].append({"role": "assistant", "content": ans})
                    backend.send_message(supabase, "AI", ans, receiver=username)
                    
                    if not is_premium:
                        supabase.table("users").update({"daily_questions": daily_questions + 1}).eq("username", username).execute()
                        st.rerun()

# ==========================================
# 2. BẠN BÈ & CHAT REAL-TIME
# ==========================================
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

    st.divider()
    
    # Danh sách bạn bè
    friends = supabase.table("friendships").select("*").eq("status", "accepted").or_(f"sender.eq.{username},receiver.eq.{username}").execute().data
    friend_list = [f['receiver'] if f['sender'] == username else f['sender'] for f in friends]
    
    if friend_list:
        target_friend = st.selectbox("Chọn bạn bè để chat:", friend_list)
        
        # TỰ ĐỘNG CẬP NHẬT MỖI 3 GIÂY
        st_autorefresh(interval=3000, key="chat_refresh")
        
        # Khung hiển thị tin nhắn
        chat_container = st.container(height=400)
        with chat_container:
            messages = backend.get_messages(supabase, receiver=target_friend)
            for m in messages:
                is_me = m['sender'] == username
                with st.chat_message("user" if is_me else "assistant"):
                    st.caption(f"**{m['sender']}**")
                    if m.get('content'): st.markdown(m['content'])
                    if m.get('file_url'):
                        if m.get('msg_type') == 'image':
                            st.image(m['file_url'], width=200)
                        else: 
                            st.markdown(f"[📁 Tải xuống file]({m['file_url']})")
                    
        # Form gửi tin nhắn
        with st.form("chat_form", clear_on_submit=True):
            col_msg, col_file = st.columns([3, 1])
            with col_msg:
                msg = st.text_input("Nhập tin nhắn...", label_visibility="collapsed")
            with col_file:
                file = st.file_uploader("Đính kèm", type=["jpg", "png", "pdf", "docx"], label_visibility="collapsed")
            
            if st.form_submit_button("Gửi", use_container_width=True):
                file_url = None
                msg_type = "text"
                if file:
                    if file.size > 2 * 1024 * 1024:
                        st.error("File quá lớn! Tối đa 2MB."); st.stop()
                    f_bytes = file.read()
                    ext = file.name.split('.')[-1]
                    f_name = f"chat_{username}_{int(time.time())}.{ext}"
                    supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                    file_url = supabase.storage.from_("public_images").get_public_url(f_name)
                    msg_type = "image" if ext in ["jpg", "png"] else "file"
                
                if msg or file_url:
                    backend.send_message(supabase, username, msg, receiver=target_friend, file_url=file_url, msg_type=msg_type)
                    st.rerun()
    else:
        st.info("Bạn chưa có người bạn nào. Hãy kết bạn nhé!")

# ==========================================
# 3. NHÓM HỌC TẬP & CHAT NHÓM
# ==========================================
def render_groups(supabase, username, is_admin):
    st.header("Nhóm học tập & Chat nhóm")
    
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
    
    groups = supabase.table("groups").select("*").order("created_at", desc=True).execute().data
    if not groups: return
    
    group_dict = {g['group_name']: g['id'] for g in groups}
    selected_group_name = st.selectbox("Chọn nhóm để tham gia/chat", list(group_dict.keys()))
    selected_group_id = group_dict[selected_group_name]
    
    is_member = supabase.table("group_members").select("*").eq("group_id", selected_group_id).eq("username", username).execute().data
    
    if not is_member:
        st.warning("Bạn chưa tham gia nhóm này.")
        if st.button("Tham gia nhóm ngay", type="primary"):
            supabase.table("group_members").insert({"group_id": selected_group_id, "username": username}).execute()
            st.success("Đã tham gia nhóm!"); time.sleep(1); st.rerun()
    else:
        st.success(f"Bạn đã là thành viên của nhóm: {selected_group_name}")
        st.divider()
        
        st_autorefresh(interval=3000, key="group_refresh")
        
        chat_container = st.container(height=400)
        with chat_container:
            messages = backend.get_messages(supabase, group_id=selected_group_id)
            for m in messages:
                is_me = m['sender'] == username
                with st.chat_message("user" if is_me else "assistant"):
                    st.caption(f"**{m['sender']}**")
                    if m.get('content'): st.markdown(m['content'])
                    if m.get('file_url'):
                        if m.get('msg_type') == 'image': st.image(m['file_url'], width=200)
                        else: st.markdown(f"[📁 Tải xuống file]({m['file_url']})")
                    
        with st.form("group_chat_form", clear_on_submit=True):
            msg = st.text_input("Nhắn gì đó cho cả nhóm...")
            file = st.file_uploader("Gửi ảnh/file", type=["jpg", "png", "pdf", "docx"])
            if st.form_submit_button("Gửi"):
                file_url = None
                msg_type = "text"
                if file:
                    if file.size > 2 * 1024 * 1024:
                        st.error("File quá lớn! Tối đa 2MB."); st.stop()
                    f_bytes = file.read()
                    ext = file.name.split('.')[-1]
                    f_name = f"group_{username}_{int(time.time())}.{ext}"
                    supabase.storage.from_("public_images").upload(file=f_bytes, path=f_name)
                    file_url = supabase.storage.from_("public_images").get_public_url(f_name)
                    msg_type = "image" if ext in ["jpg", "png"] else "file"
                
                backend.send_message(supabase, username, msg, group_id=selected_group_id, file_url=file_url, msg_type=msg_type)
                st.rerun()

# Các hàm render_image_solver, render_rooms, render_forum, render_profile, render_admin giữ nguyên
