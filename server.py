import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# التوكن ورابط السيرفر
TELEGRAM_TOKEN = "8977841816:AAHTSoTngUCO6zUhE-zESC56jSdttqpm6LI"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
SERVER_URL = "https://pos-licensing-server-uroy.onrender.com"

def send_telegram_msg(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=5)
    except Exception as e:
        print("Error sending message:", e)

def edit_telegram_msg(chat_id, message_id, text):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(f"{TELEGRAM_API}/editMessageText", json=payload, timeout=5)
    except Exception as e:
        print("Error editing message:", e)

# --- سيرفر الفلاسك (API) ---
@app.route('/')
def home():
    return "Licensing Server & Telegram Bot are Running Live!"

# استقبال تحديثات تليجرام عبر Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return 'bad request', 400

    # التعامل مع الرسائل العادية
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text.startswith("/start"):
            reply = (
                "👋 **أهلاً بك في نظام إدارة اشتراكات الكاشير!**\n\n"
                "الأوامر المتاحة:\n"
                "• `/branches` - عرض الفروع وحالات التجديد\n"
                "• `/renew <client_id>` - تجديد اشتراك لفرع معين"
            )
            send_telegram_msg(chat_id, reply)

        elif text.startswith("/branches"):
            try:
                res = requests.get(f"{SERVER_URL}/branches", timeout=5)
                b_data = res.json()
                if not b_data:
                    send_telegram_msg(chat_id, "لا يوجد عملاء مسجلين حالياً.")
                else:
                    reply = "📊 **قائمة اشتراكات الفروع:**\n\n"
                    for client in b_data:
                        status = "🟢 نشط" if client.get('is_active') else "🔴 منتهي"
                        reply += f"🏢 **الفرع:** {client.get('branch_name', 'غير مسمى')}\n"
                        reply += f"🔑 **ID:** `{client.get('client_id')}`\n"
                        reply += f"الحالة: {status}\n"
                        reply += "-----------------------------------\n"
                    send_telegram_msg(chat_id, reply)
            except Exception as e:
                send_telegram_msg(chat_id, f"خطأ في جلب الفروع: {e}")

        elif text.startswith("/renew"):
            parts = text.split()
            if len(parts) < 2:
                send_telegram_msg(chat_id, "يرجى كتابة الـ Client ID مع الأمر، مثال:\n`/renew 123456`")
            else:
                client_id = parts[1]
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "10 دقائق", "callback_data": f"renew_10_دقيقة_{client_id}"},
                            {"text": "ساعة", "callback_data": f"renew_1_ساعة_{client_id}"}
                        ],
                        [
                            {"text": "يوم", "callback_data": f"renew_1_يوم_{client_id}"},
                            {"text": "أسبوع", "callback_data": f"renew_1_أسبوع_{client_id}"}
                        ],
                        [
                            {"text": "شهر", "callback_data": f"renew_1_شهر_{client_id}"},
                            {"text": "3 شهور", "callback_data": f"renew_3_شهر_{client_id}"}
                        ]
                    ]
                }
                send_telegram_msg(chat_id, f"اختر مدة التجديد للعميل `{client_id}`:", reply_markup=keyboard)

    # التعامل مع أزرار Inline
    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]
        cb_data = cb["data"].split('_')

        if len(cb_data) >= 4:
            amount = int(cb_data[1])
            unit = cb_data[2]
            client_id = cb_data[3]

            payload = {"client_id": client_id, "amount": amount, "unit": unit}
            try:
                res = requests.post(f"{SERVER_URL}/renew", json=payload, timeout=5)
                res_data = res.json()

                if res_data.get("status") == "success":
                    text = (
                        f"✅ **تم التجديد بنجاح!**\n\n"
                        f"🔑 العميل: `{client_id}`\n"
                        f"➕ المضافة: {amount} {unit}\n"
                        f"📅 الانتهاء الجديد: {res_data.get('new_expiry')}"
                    )
                else:
                    text = "❌ فشلت عملية التجديد."
                edit_telegram_msg(chat_id, msg_id, text)
            except Exception as e:
                edit_telegram_msg(chat_id, msg_id, f"خطأ: {e}")

    return 'ok', 200

# تفعيل الـ Webhook عند بداية تشغيل الملف
try:
    requests.get(f"{TELEGRAM_API}/setWebhook?url={SERVER_URL}/webhook", timeout=10)
except Exception as e:
    print("Webhook Setup Error:", e)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
