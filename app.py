import streamlit as st
import os
import time
import base64
import requests
from datetime import datetime, timedelta, timezone
from PIL import Image
import google.generativeai as genai
from supabase import create_client
from st_login_form import login_form
from openai import OpenAI
import streamlit.components.v1 as components # Thay thế streamlit_embedcode

# ===== 1. CẤU HÌNH TRANG =====
st.set_page_config(page_title="Gia Sư AI", page_icon="🧠", layout="wide")

# ===== 2. KHỞI TẠO KẾT NỐI =====
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error(f"❌ Lỗi cấu hình: {e}")
    st.stop()

# ===== 3. ĐĂNG NHẬP =====
try:
    client_auth = login_form()
except Exception as e:
    if "23505" in str(e) or "duplicate key" in str(e):
        st.toast("❌ Tên đăng nhập này đã tồn tại!", icon="⚠️")
    else:
        st.toast(f"❌ Lỗi đăng nhập: {e}", icon="⚠️")
    st.stop()

if not st.session_state.get("authenticated"):
    st.info("👋 Vui lòng đăng nhập/đăng ký để nhận 7 ngày dùng thử (Premium).")
    st.stop()

username = st.session_state.get("username")

# ===== 4. QUẢN LÝ GÓI DỊCH VỤ =====
try:
    res = supabase.table("user_subscriptions").select("*").eq("username", username).execute()
    now = datetime.now(timezone.utc)
    is_premium = False

    if len(res.data) == 0:
        trial_end = now + timedelta(days=7)
        supabase.table("user_subscriptions").insert({
            "username": username, "email": username, "trial_start": now.isoformat(),
            "plan_type": "trial", "expiry_date": trial_end.isoformat()
        }).execute()
        st.toast("🎁 Đã kích hoạt 7 ngày dùng thử Premium!", icon="✅")
        is_premium = True
        plan_type = "Trial (7 ngày)"
    else:
        user_data = res.data[0]
        expiry_date = datetime.fromisoformat(user_data["expiry_date"].replace('Z', '+00:00'))
        plan_type = user_data["plan_type"]
        
        if now > expiry_date:
            is_premium = False
            plan_type = "Miễn phí (Free)"
        else:
            is_premium = True
            days_left = (expiry_date - now).days
            plan_type = f"{plan_type.capitalize()} (Còn {days_left} ngày)"
except Exception as e:
    st.toast(f"Lỗi dữ liệu: {e}", icon="❌")
    st.stop()

# ===== 5. SIDEBAR =====
with st.sidebar:
    st.title("🧠 Gia Sư AI")
    st.success(f"Chào, **{username}**!")
    st.markdown(f"**Gói:** `{plan_type}`")
    
    if not is_premium:
        st.warning("Bạn đang dùng bản Miễn phí (Giới hạn 100 câu hỏi/ngày). Nâng cấp để mở khóa toàn bộ!")
        if st.button("💳 Nâng cấp Premium (20k/tháng)", use_container_width=True):
            try:
                auth_str = f"{st.secrets['APIPAY_ACCESS_KEY']}:{st.secrets['APIPAY_SECRET_KEY']}"
                auth_base64 = base64.b64encode(auth_str.encode()).decode()
                headers = {"Authorization": f"Bearer {auth_base64}", "Content-Type": "application/json"}
                
                payload = {
                    "bankPublicId": "bank_abc123",  # Thay bằng mã ngân hàng thật của ApiPay
                    "amount": 20000,
                    "content": f"UPGRADE_{username}"
                }
                
                with st.spinner("Đang tạo mã thanh toán..."):
                    response = requests.post("https://app.apipay.vn/v1/client/payment-requests", json=payload, headers=headers)
                    if response.status_code == 200:
                        pay_url = response.json().get("payUrl")
                        st.markdown(f'<meta http-equiv="refresh" content="0; url={pay_url}">', unsafe_allow_html=True)
                    else:
                        st.toast("Lỗi tạo thanh toán. Vui lòng kiểm tra lại ApiPay.", icon="❌")
            except Exception as e:
                st.toast(f"Lỗi ApiPay: {e}", icon="❌")
    
    st.divider()
    st.subheader("🤖 Chọn Trợ lý AI")
    provider = st.selectbox("Nền tảng", ["Google Gemini 2.0", "Groq (Llama 3.3)", "OpenRouter"])
    
    st.divider()
    with st.expander("📞 Liên hệ Admin"):
        st.write("Zalo/Hotline: **0123.456.789**")
        st.write("Email: **admin@giasuai.com**")
        st.write("Group FB hỗ trợ: [Bấm vào đây](https://facebook.com)")
        
    if st.button("Đăng xuất", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ===== 6. HÀM GỌI AI =====
def get_ai_response(prompt, image=None, provider="gemini"):
    try:
        if provider == "Google Gemini 2.0":
            model = genai.GenerativeModel('gemini-2.0-flash')
            content = [prompt]
            if image: content.append(image)
            return model.generate_content(content).text
            
        elif provider == "Groq (Llama 3.3)":
            if image: return "⚠️ Groq không hỗ trợ đọc ảnh. Chọn Gemini!"
            client = OpenAI(api_key=st.secrets["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            return res.choices[0].message.content
            
        elif provider == "OpenRouter":
            if image: return "⚠️ OpenRouter không hỗ trợ đọc ảnh. Chọn Gemini!"
            client = OpenAI(api_key=st.secrets["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
            res = client.chat.completions.create(model="meta-llama/llama-3.3-70b-instruct:free", messages=[{"role": "user", "content": prompt}])
            return res.choices[0].message.content
    except Exception as e:
        st.toast(f"Lỗi AI: {str(e)[:100]}...", icon="❌")
        return "Hiện tại không thể kết nối với AI. Vui lòng thử lại sau giây lát."

# ===== 7. GIAO DIỆN CHÍNH (TABS) =====
tab_chat, tab_vision, tab_room, tab_forum = st.tabs([
    "💬 Chat Gia Sư", "📸 Giải Bài Tập", "🎥 Phòng Học Tập", "📚 Diễn Đàn & Tài Liệu"
])

# --- TAB 1: CHAT ---
with tab_chat:
    if "chat_count" not in st.session_state: st.session_state.chat_count = 0
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Chào bạn! Mình có thể giúp gì hôm nay?"}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if not is_premium and st.session_state.chat_count >= 100:
        st.warning("🛑 Bạn đã đạt giới hạn 100 câu hỏi/ngày của bản Miễn phí. Nâng cấp Premium để chat không giới hạn.")
    else:
        if prompt := st.chat_input("Hỏi bài (VD: Giải thích định lý Pytago)"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
                
            with st.chat_message("assistant"):
                with st.spinner("Đang suy nghĩ..."):
                    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
                    full_prompt = f"Bạn là gia sư thân thiện. Lịch sử:\n{history_text}\n\nTrả lời câu hỏi mới nhất."
                    response_text = get_ai_response(full_prompt, provider=provider)
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    if not is_premium: st.session_state.chat_count += 1

# --- TAB 2: GIẢI BÀI TẬP QUA ẢNH ---
with tab_vision:
    if not is_premium:
        st.error("🔒 Tính năng này chỉ dành cho Premium.")
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

# --- TAB 3: PHÒNG HỌC TẬP (DÙNG COMPONENTS.HTML) ---
with tab_room:
    st.subheader("Phòng Học Nhóm Trực Tuyến")
    st.info("Tính năng này cho phép bật Camera, Mic và Chia sẻ màn hình (Hoàn toàn miễn phí).")
    
    room_name = st.text_input("Nhập tên phòng (VD: onthi_toan12)", value="GiaSuAI_PhongChung")
    
    if st.button("Tham Gia Phòng"):
        st.write(f"Đang kết nối vào phòng: **{room_name}**...")
        # Mã HTML để nhúng Jitsi Meet
        jitsi_html = f"""
        <div id="jitsi-container" style="width: 100%; height: 600px;"></div>
        <script src="https://meet.jit.si/external_api.js"></script>
        <script>
            const domain = "meet.jit.si";
            const options = {{
                roomName: "{room_name}",
                parentNode: document.querySelector('#jitsi-container'),
                width: "100%",
                height: 600,
                configOverwrite: {{
                    startWithAudioMuted: true,
                    startWithVideoMuted: false
                }},
                interfaceConfigOverwrite: {{
                    DISABLE_JOIN_LEAVE_NOTIFICATIONS: true
                }}
            }};
            const api = new JitsiMeetExternalAPI(domain, options);
        </script>
        """
        components.html(jitsi_html, height=620)

# --- TAB 4: DIỄN ĐÀN & TÀI LIỆU ---
with tab_forum:
    st.subheader("Diễn Đàn Hỏi Đáp & Chia Sẻ Đề Thi")
    
    with st.expander("➕ Đăng bài viết mới"):
        title = st.text_input("Tiêu đề bài viết")
        content = st.text_area("Nội dung (Có thể dán link tài liệu/đề thi vào đây)")
        if st.button("Đăng bài"):
            if title and content:
                try:
                    supabase.table("forum_posts").insert({
                        "username": username, "title": title, "content": content
                    }).execute()
                    st.toast("✅ Đăng bài thành công!", icon="🎉")
                    st.rerun()
                except Exception as e:
                    st.toast(f"Lỗi đăng bài: {e}", icon="❌")
            else:
                st.toast("Vui lòng nhập đủ tiêu đề và nội dung!", icon="⚠️")
                
    st.divider()
    
    try:
        posts = supabase.table("forum_posts").select("*").order("created_at", desc=True).execute()
        
        if not posts.data:
            st.info("Chưa có bài đăng nào. Hãy là người đầu tiên chia sẻ!")
            
        for post in posts.data:
            with st.container(border=True):
                st.markdown(f"### {post['title']}")
                st.caption(f"Đăng bởi: **{post['username']}** | Lúc: {post['created_at'][:16].replace('T', ' ')}")
                st.write(post['content'])
                
                with st.expander(f"💬 Bình luận"):
                    comments = supabase.table("forum_comments").select("*").eq("post_id", post['id']).order("created_at").execute()
                    for cmt in comments.data:
                        st.markdown(f"**{cmt['username']}**: {cmt['comment']}")
                        
                    new_cmt = st.text_input("Viết bình luận...", key=f"cmt_{post['id']}")
                    if st.button("Gửi", key=f"btn_{post['id']}"):
                        if new_cmt:
                            supabase.table("forum_comments").insert({
                                "post_id": post['id'], "username": username, "comment": new_cmt
                            }).execute()
                            st.rerun()
    except Exception as e:
        st.toast(f"Lỗi tải diễn đàn: {e}", icon="❌")
