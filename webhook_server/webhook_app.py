import os
from flask import Flask, request, jsonify
from supabase import create_client

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/webhook", methods=["POST"])
def apipay_webhook():
    try:
        data = request.json
        print("Nhận tín hiệu từ ApiPay:", data)
        
        # BẢO MẬT: Kiểm tra số tiền (ít nhất 10.000đ) để tránh bị spam mã giả
        amount = data.get("amount", 0) 
        order_content = data.get("content", "") or data.get("description", "")
        
        if "UPGRADE_" in order_content and amount >= 10000:
            parts = order_content.split("_")
            if len(parts) >= 2:
                username = parts[1]
                # Cập nhật VIP
                supabase.table("users").update({"is_premium": True}).eq("username", username).execute()
                print(f"✅ Đã nâng cấp VIP cho: {username} (Số tiền: {amount})")
                return jsonify({"status": "success"}), 200
        
        return jsonify({"status": "ignored", "reason": "Invalid amount or content"}), 200
    except Exception as e:
        print("Lỗi:", str(e))
        return jsonify({"status": "error"}), 500

@app.route("/", methods=["GET"])
def health_check():
    return "Webhook is running safely!", 200
