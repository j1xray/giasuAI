import os
from flask import Flask, request, jsonify
from supabase import create_client

app = Flask(__name__)

# Lấy biến môi trường (Sẽ điền trên Render)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/webhook", methods=["POST"])
def apipay_webhook():
    try:
        data = request.json
        print("Nhận tín hiệu:", data)
        
        order_content = data.get("content", "") or data.get("description", "")
        
        if "UPGRADE_" in order_content:
            parts = order_content.split("_")
            if len(parts) >= 2:
                username = parts[1]
                supabase.table("users").update({"is_premium": True}).eq("username", username).execute()
                print(f"✅ Đã nâng cấp VIP cho: {username}")
                return jsonify({"status": "success"}), 200
        
        return jsonify({"status": "ignored"}), 200
    except Exception as e:
        print("Lỗi:", str(e))
        return jsonify({"status": "error"}), 500

@app.route("/", methods=["GET"])
def health_check():
    return "Webhook is running!", 200
