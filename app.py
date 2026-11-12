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

# ===== 1. CẤU HÌNH TRANG =====
st.set_page_config(page_title="Gia Sư AI", page_icon="🧠", layout="wide")

# ===== 2. KHỞI TẠO KẾT NỐI =====
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except KeyError as e:
    st.error(f"❌ Lỗi cấu hình: Thiếu biến {e} trong Streamlit Secrets.")
    st.stop()
except Exception as e:
    st.error(f"❌ Lỗi kết nối CSDL: {e}")
    st.stop()

# ===== 3. ĐĂNG NHẬP / ĐĂNG KÝ =====
# ===== 3. ĐĂNG NHẬP / ĐĂNG KÝ =====
try:
    client_auth = login_form()
except Exception as e:
    # Bắt lỗi trùng tên đăng nhập (Mã lỗi 23505 của Postgres)
    if "23505" in str(e) or "duplicate key" in str(e):
        st.error("❌ Tên đăng nhập này đã tồn tại! Vui lòng chọn tên khác hoặc chuyển sang tab Đăng nhập.")
    else:
        st.error(f"❌ Lỗi đăng nhập/đăng ký: {e}")
    st.stop()

if not st.session_state.get("authenticated"):
    st.info("👋 Chào mừng bạn đến với Gia Sư AI. Vui lòng đăng nhập/đăng ký để nhận 7 ngày dùng thử (Premium).")
    st.stop()
# Lấy username thay vì user_id
username = st.session_state.get("username")
if not username:
    st.error("Không tìm thấy thông tin đăng nhập. Vui lòng đăng nhập lại.")
    st.stop()

# ===== 4. QUẢN LÝ GÓI DỊCH VỤ (FREEMIUM) =====
try:
    # Truy vấn bằng username
    res = supabase.table("user_subscriptions").select("*").eq("username", username).execute()
    now = datetime.now(timezone.utc)
    is_premium = False

    if len(res.data) == 0:
        # Người dùng mới -> Cấp Trial 7 ngày
        trial_end = now + timedelta(days=7)
        supabase.table("user_subscriptions").insert({
            "username": username, 
            "email": username, # Tạm dùng username làm email nếu không có
            "trial_start": now.isoformat(),
            "plan_type": "trial", 
            "expiry_date": trial_end.isoformat()
        }).execute()
        st.toast("🎁 Chúc mừng! Bạn đã được nâng cấp lên gói Trial (Premium) 7 ngày.", icon="✅")
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
    st.error(f"Lỗi truy xuất dữ liệu người dùng: {e}")
    st.stop()

# ===== 5. SIDEBAR (THANH ĐIỀU HƯỚNG) =====
with st.sidebar:
    st.title("🧠 Gia Sư AI")
    st.success(f"Chào, **{username}**!")
    st.markdown(f"**Gói hiện tại:** `{plan_type}`")
    
    # Nút nâng cấp (ApiPay)
    if not is_premium:
        st.warning("Bạn đang dùng bản Miễn phí (Giới hạn 100 câu hỏi/ngày). Nâng cấp để mở khóa toàn bộ!")
        if st.button("💳 Nâng cấp Premium (20k/tháng)", use_container_width=True):
            try:
                auth_str = f"{st.secrets['APIPAY_ACCESS_KEY']}:{st.secrets['APIPAY_SECRET_KEY']}"
                auth_base64 = base64.b64encode(auth_str.encode()).decode()
                headers = {"Authorization": f"Bearer {auth_base64}", "Content-Type": "application/json"}
                
                payload = {
                    "bankPublicId": "bank_abc123",  # Thay bằng mã ngân hàng của bạn trên ApiPay
                    "amount": 20000,
                    "content": f"UPGRADE_{username}" # Dùng username làm nội dung chuyển khoản
                }
                
                with st.spinner("Đang tạo mã thanh toán..."):
                    response = requests.post("https://app.apipay.vn/v1/client/payment-requests", json=payload, headers=headers)
                    if response.status_code == 200:
                        pay_url = response.json().get("payUrl")
                        st.markdown(f'<meta http-equiv="refresh" content="0; url={pay_url}">', unsafe_allow_html=True)
                    else:
                        st.error("Lỗi tạo thanh toán. Vui lòng kiểm tra lại ApiPay.")
            except Exception as e:
                st.error(f"Lỗi ApiPay: {e}")
    
    st.divider()
    
    st.subheader("🤖 Chọn Trợ lý AI")
    provider = st.selectbox("Nền tảng AI", ["Google Gemini (Khuyên dùng)", "Groq (Llama 3)", "OpenRouter (Mixtral)"])
    
    if st.button("Đăng xuất", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ===== 6. HÀM GỌI AI ĐA NỀN TẢNG =====
def get_ai_response(prompt, image=None, provider="gemini"):
    try:
        if provider == "Google Gemini (Khuyên dùng)":
            model = genai.GenerativeModel('gemini-1.5-flash')
            content = [prompt]
            if image: content.append(image)
            response = model.generate_content(content)
            return response.text
            
        elif provider == "Groq (Llama 3)":
            if image: return "⚠️ Llama 3 trên Groq không hỗ trợ đọc ảnh. Vui lòng chọn Gemini!"
            client = OpenAI(api_key=st.secrets["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
            response = client.chat.completions.create(model="llama3-70b-8192", messages=[{"role": "user", "content": prompt}])
            return response.choices[0].message.content
            
        elif provider == "OpenRouter (Mixtral)":
            if image: return "⚠️ Mixtral trên OpenRouter không hỗ trợ đọc ảnh. Vui lòng chọn Gemini!"
            client = OpenAI(api_key=st.secrets["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
            response = client.chat.completions.create(model="mistralai/mistral-7b-instruct:free", messages=[{"role": "user", "content": prompt}])
            return response.choices[0].message.content
    except Exception as e:
        return f"❌ Lỗi kết nối AI: {str(e)}"

# ===== 7. GIAO DIỆN CHÍNH (TABS) =====
tab_chat, tab_file, tab_vision = st.tabs(["💬 Chat Gia Sư", "📄 Đọc Tài Liệu", "📸 Giải Bài Tập Qua Ảnh"])

# --- TAB 1: CHAT ---
with tab_chat:
    st.subheader("Trò chuyện cùng Gia Sư")
    
    if "chat_count" not in st.session_state: st.session_state.chat_count = 0
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Chào bạn! Mình có thể giúp gì cho việc học hôm nay?"}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if not is_premium and st.session_state.chat_count >= 100:
        st.warning("🛑 Bạn đã đạt giới hạn 100 câu hỏi/ngày của bản Miễn phí. Nâng cấp Premium để chat không giới hạn.")
    else:
        if prompt := st.chat_input("Hỏi bài (VD: Giải thích định lý Pytago)"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
                
            with st.chat_message("assistant"):
                with st.spinner("Đang suy nghĩ..."):
                    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
                    full_prompt = f"Bạn là gia sư thân thiện. Lịch sử trò chuyện:\n{history_text}\n\nHãy trả lời câu hỏi mới nhất của học sinh."
                    
                    response_text = get_ai_response(full_prompt, provider=provider)
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    
                    if not is_premium: st.session_state.chat_count += 1

# --- TAB 2: ĐỌC TÀI LIỆU (PREMIUM) ---
with tab_file:
    st.subheader("Phân tích tài liệu (PDF)")
    if not is_premium:
        st.error("🔒 Tính năng này chỉ dành cho tài khoản Premium. Vui lòng nâng cấp để sử dụng.")
    else:
        uploaded_file = st.file_uploader("Tải lên tài liệu (PDF)", type=["pdf"])
        if uploaded_file and st.button("Tóm tắt tài liệu"):
            with st.spinner("AI đang đọc và tóm tắt tài liệu..."):
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                try:
                    gemini_file = genai.upload_file(path=tmp_path)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(["Tóm tắt các ý chính của tài liệu này:", gemini_file])
                    st.success("Hoàn tất!")
                    st.markdown(response.text)
                    os.unlink(tmp_path)
                except Exception as e:
                    st.error(f"Lỗi: {e}")

# --- TAB 3: GIẢI BÀI TẬP QUA ẢNH (PREMIUM) ---
with tab_vision:
    st.subheader("Giải bài tập qua ảnh")
    if not is_premium:
        st.error("🔒 Tính năng này chỉ dành cho tài khoản Premium. Vui lòng nâng cấp để sử dụng.")
    else:
        img_source = st.radio("Nguồn ảnh:", ["Chụp ảnh", "Tải ảnh lên"], horizontal=True)
        image_data = st.camera_input("Chụp bài tập của bạn") if img_source == "Chụp ảnh" else st.file_uploader("Tải ảnh", type=["jpg", "png", "jpeg"])

        if image_data:
            img = Image.open(image_data)
            st.image(img, caption="Ảnh bài tập", width=300)
            
            if st.button("Giải bài này"):
                with st.spinner("Đang phân tích hình ảnh..."):
                    prompt = "Hãy đọc nội dung bài tập trong ảnh, sau đó hướng dẫn cách giải chi tiết từng bước một."
                    response_text = get_ai_response(prompt, image=img, provider=provider)
                    st.markdown("### 🎓 Lời giải chi tiết:")
                    st.markdown(response_text)
