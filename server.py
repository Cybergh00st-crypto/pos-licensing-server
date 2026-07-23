import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# التوكن ورابط السيرفر
TELEGRAM_TOKEN = "8977841816:AAHTSoTngUCO6zUhE-zESC56jSdttqpm6LI"
SERVER_URL = "https://pos-licensing-server-uroy.onrender.com"

# --- سيرفر الفلاسك (API) ---
@app.route('/')
def home():
    return "Licensing Server & Telegram Bot are Running Live!"

# استقبال تحديثات تليجرام عبر Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({}), 200

    # التعامل مع الرسائل النصية العادية
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text.startswith("/start"):
            reply_text = (
                "👋 **أهلاً بك في نظام إدارة اشتراكات الكاشير!**\n\n"
                "الأوامر المتاحة:\n"
                "• `/branches` - عرض الفروع وحالات التجديد\n"
                "• `/renew <client_id>` - تجديد اشتراك لفرع معين"
            )
            return jsonify({
                "method": "sendMessage",
                "chat_id": chat_id,
                "text": reply_text,
                "parse_mode": "Markdown"
            })

        elif text.startswith("/branches"):
            try:
                res = requests.get(f"{SERVER_URL}/branches", timeout=5)
                b_data = res.json()
                if not b_data:
                    reply_text = "لا يوجد عملاء مسجلين حالياً."
                else:
                    reply_text = "📊 **قائمة اشتراكات الفروع:**\n\n"
                    for client in b_data:
                        status = "🟢 نشط" if client.get('is_active') else "🔴 منتهي"
                        reply_text += f"🏢 **الفرع:** {client.get('branch_name', 'غير مسمى')}\n"
                        reply_text += f"🔑 **ID:** `{client.get('client_id')}`\n"
                        reply_text += f"الحالة: {status}\n"
                        reply_text += "-----------------------------------\n"
            except Exception as e:
                reply_text = f"خطأ في جلب الفروع: {e}"

            return jsonify({
                "method": "sendMessage",
                "chat_id": chat_id,
                "text": reply_text,
                "parse_mode": "Markdown"
            })

        elif text.startswith("/renew"):
            parts = text.split()
            if len(parts) < 2:
                reply_text = "يرجى كتابة الـ Client ID مع الأمر، مثال:\n`/renew 123456`"
                return jsonify({
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": reply_text,
                    "parse_mode": "Markdown"
                })
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
                return jsonify({
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": f"اختر مدة التجديد للعميل `{client_id}`:",
                    "reply_markup": keyboard,
                    "parse_mode": "Markdown"
                })

    # التعامل مع الضغط على أزرار Inline
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
                    reply_text = (
                        f"✅ **تم التجديد بنجاح!**\n\n"
                        f"🔑 العميل: `{client_id}`\n"
                        f"➕ المضافة: {amount} {unit}\n"
                        f"📅 الانتهاء الجديد: {res_data.get('new_expiry')}"
                    )
                else:
                    reply_text = "❌ فشلت عملية التجديد."
            except Exception as e:
                reply_text = f"خطأ: {e}"

            return jsonify({
                "method": "editMessageText",
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": reply_text,
                "parse_mode": "Markdown"
            })

    return jsonify({}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
