import threading
from flask import Flask, request, jsonify
from pyngrok import ngrok
from supabase import create_client
import json

# ===== 1. CẤU HÌNH =====
NGROK_TOKEN = "YOUR_NGROK_TOKEN" # Lấy tại dashboard.ngrok.com
SUPABASE_URL = "https://okwhgyxhvfzgzpkgrgpb.supabase.co"
SUPABASE_KEY = "eyJhbGciOi..." # Điền key anon của bạn

# Khởi tạo Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Khởi tạo Flask App
app = Flask(__name__)

# ===== 2. TẠO ĐƯỜNG DẪN NHẬN WEBHOOK =====
@app.route("/webhook", methods=["POST"])
def apipay_webhook():
    try:
        data = request.json
        print("Nhận được tín hiệu từ ApiPay:", data)

        # ApiPay thường trả về mã đơn hàng hoặc nội dung chuyển khoản trong data
        # Tùy vào cấu trúc của ApiPay, bạn có thể cần sửa lại key này (VD: data['content'] hoặc data['orderCode'])
        order_content = data.get("content", "") or data.get("description", "")
        
        # Nội dung chuyển khoản của chúng ta có dạng: UPGRADE_username_timestamp
        if "UPGRADE_" in order_content:
            # Tách lấy username
            parts = order_content.split("_")
            if len(parts) >= 2:
                username = parts[1]
                
                # Cập nhật Database (Bật Premium)
                supabase.table("users").update({"is_premium": True}).eq("username", username).execute()
                print(f"✅ Đã nâng cấp Premium cho user: {username}")
                
                return jsonify({"status": "success", "message": "User upgraded"}), 200
        
        return jsonify({"status": "ignored", "message": "Not an upgrade code"}), 200

    except Exception as e:
        print("❌ Lỗi xử lý webhook:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

# ===== 3. CHẠY SERVER VÀ MỞ CỔNG NGROK =====
def run_flask():
    app.run(port=5000)

# Chạy Flask trong một luồng riêng để không treo Colab
thread = threading.Thread(target=run_flask, daemon=True)
thread.start()

# Kết nối Ngrok
ngrok.set_auth_token(NGROK_TOKEN)
ngrok.kill() # Xóa các kết nối cũ nếu có
public_url = ngrok.connect(5000).public_url
print(f"\n🚀 SERVER ĐANG CHẠY!")
print(f"👉 Link Webhook của bạn là: {public_url}/webhook")
print("👉 Hãy copy link này và dán vào phần cấu hình Webhook trên ApiPay.")
