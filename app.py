
import streamlit as st
import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import PyPDFLoader, TextLoader
import tempfile

# ===== CẤU HÌNH TRANG =====
st.set_page_config(page_title="Gia Sư AI", page_icon="🧠")
st.title("🧠 Chatbot Gia Sư Cá Nhân")
st.caption("Tải lên tài liệu môn học và đặt câu hỏi. AI sẽ trả lời dựa trên chính tài liệu của bạn.")

# ===== LẤY API KEY =====
# Ưu tiên lấy từ Streamlit Secrets (khi deploy), nếu không có thì cho người dùng nhập
if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.text_input("Nhập Gemini API Key của bạn:", type="password")
    if not api_key:
        st.info("Vui lòng nhập API Key để bắt đầu. Bạn có thể lấy key miễn phí tại aistudio.google.com/app/apikey")
        st.stop()
    os.environ["GOOGLE_API_KEY"] = api_key

# Khởi tạo LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

# ===== PHẦN TẢI TÀI LIỆU VÀ XỬ LÝ =====
uploaded_file = st.file_uploader("Tải lên tài liệu (PDF hoặc TXT)", type=["pdf", "txt"])

if uploaded_file is not None:
    if "vector_store" not in st.session_state:
        with st.spinner("Đang xử lý tài liệu... (Lần đầu có thể mất 1-2 phút)"):
            # Lưu file tạm
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            # Đọc tài liệu
            if uploaded_file.name.endswith('.pdf'):
                loader = PyPDFLoader(tmp_file_path)
            else:
                loader = TextLoader(tmp_file_path, encoding='utf-8')
            
            documents = loader.load()
            
            # Chia nhỏ văn bản
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            texts = text_splitter.split_documents(documents)
            
            # Tạo embeddings và lưu vào Vector Database
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            vector_store = Chroma.from_documents(documents=texts, embedding=embeddings, persist_directory="./chroma_db")
            
            st.session_state.vector_store = vector_store
            st.success("Xử lý tài liệu hoàn tất! Bạn có thể bắt đầu đặt câu hỏi.")
            os.unlink(tmp_file_path)

    # ===== PHẦN HỎI ĐÁP =====
    if "vector_store" in st.session_state:
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=st.session_state.vector_store.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=True
        )
        
        query = st.text_input("Nhập câu hỏi của bạn về môn học:")
        if query:
            with st.spinner("Đang suy nghĩ..."):
                result = qa_chain({"query": query})
                st.write("**Trả lời:**")
                st.write(result["result"])
                
                with st.expander("Xem nguồn tham khảo"):
                    for i, doc in enumerate(result["source_documents"]):
                        st.write(f"**Đoạn {i+1}:** {doc.page_content[:300]}...")
