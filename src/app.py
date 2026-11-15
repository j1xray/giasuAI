import streamlit as st
import time
import random
import backend
import ui
import views

# 1. Cấu hình trang
st.set_page_config(page_title="Gia Sư AI 2.0", page_icon="🧠", layout="wide")
ui.load_css()

# 2. Khởi tạo
supabase = backend.init_connections()
math_brain, code_brain = backend.init_ai_brains()

# 3. Đăng nhập
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

# 4. Lấy thông tin User
username = st.session_state.get("guest_user") or st.user.email.split('@')[0]
is_admin = (st.user.email == backend.ADMIN_EMAIL) if st.user.is_logged_in else False
user_info = backend.get_user_data(supabase, username, st.user.is_logged_in)
is_premium = user_info.get("is_premium", False)
daily_questions = user_info.get("daily_questions", 0)

# 5. Header (Thanh toán)
col_header, col_btn = st.columns([8, 2])
with col_btn:
    if is_premium:
        st.success("Gói Premium")
    else:
        st.info(f"Bản Free (Câu hỏi: {daily_questions}/10)")
        if st.button("Nâng cấp (10k/tháng)", type="primary", use_container_width=True):
            with st.spinner("Đang tạo mã thanh toán..."):
                # Gọi hàm tạo link từ backend
                payment_data = backend.create_payment_link(username, 10000)
                
                if "error" in payment_data:
                    st.error(payment_data["error"])
                else:
                    # Lấy link thanh toán và chuyển hướng
                    pay_url = payment_data.get("payUrl")
                    if pay_url:
                        st.markdown(f'<meta http-equiv="refresh" content="0; url={pay_url}">', unsafe_allow_html=True)
                    else:
                        st.error("Không lấy được link thanh toán.")
# 6. Sidebar
ui.render_sidebar(user_info, username, is_admin)

# 7. Điều hướng trang (Router)
page = st.session_state.page

if page == "Trợ lý AI":
    views.render_ai(supabase, math_brain, code_brain, username, is_premium, daily_questions)
elif page == "Nhóm":
    views.render_groups(supabase, username, is_admin)
elif page == "Giải bài qua ảnh":
    views.render_image_solver()
elif page == "Phòng học nhóm":
    views.render_rooms(supabase, username)
elif page == "Diễn đàn":
    views.render_forum(supabase, username, is_admin)
elif page == "Hồ sơ":
    views.render_profile(supabase, user_info, username)
