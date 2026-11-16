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
        if st.button("👫 Bạn bè & Chat", use_container_width=True): st.session_state.page = "Bạn bè"; st.rerun()
        
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
