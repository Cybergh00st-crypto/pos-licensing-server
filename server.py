import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_TOKEN = "8977841816:AAHTSoTngUCO6zUhE-zESC56jSdttqpm6LI"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
SERVER_URL = "https://pos-licensing-server-uroy.onrender.com"

def send_msg(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=5)
        print("Send message status:", r.status_code, r.text)
    except Exception as e:
        print("Error sending message:", e)

@app.route('/')
def home():
    return "Server is Running"

@app.route('/webhook', methods=['POST'])
def webhook():
    print("--- NEW WEBHOOK REQUEST RECEIVED ---")
    data = request.get_json(force=True, silent=True) or {}
    print("Payload:", data)

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text.startswith("/start"):
            send_msg(chat_id, "👋 **أهلاً بك! البوت شغال تمام عبر الـ Webhook**")

        elif text.startswith("/branches"):
            send_msg(chat_id, "📊 جاري جلب الفروع...")

    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
