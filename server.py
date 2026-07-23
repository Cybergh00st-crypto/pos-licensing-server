import os
import asyncio
import threading
import logging
import requests
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

app = Flask(__name__)

# التوكن ورابط السيرفر
TELEGRAM_TOKEN = "8977841816:AAHTSoTngUCO6zUhE-zESC56jSdttqpm6LI"
SERVER_URL = "https://pos-licensing-server-uroy.onrender.com"

# --- سيرفر الفلاسك (API) ---
@app.route('/')
def home():
    return "Licensing Server is Running Live!"

# --- أوامر وتفاعل بوت تليجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في نظام إدارة اشتراكات الكاشير!\n\n"
        "الأوامر المتاحة:\n"
        "• /branches - عرض الفروع وحالات التجديد\n"
        "• /renew <client_id> - تجديد اشتراك لفرع معين"
    )

async def get_branches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        res = requests.get(f"{SERVER_URL}/branches", timeout=5)
        data = res.json()
        if not data:
            await update.message.reply_text("لا يوجد عملاء مسجلين حالياً.")
            return

        msg = "📊 **قائمة اشتراكات الفروع:**\n\n"
        for client in data:
            status = "🟢 نشط" if client.get('is_active') else "🔴 منتهي"
            msg += f"🏢 **الفرع:** {client.get('branch_name', 'غير مسمى')}\n"
            msg += f"🔑 **ID:** `{client.get('client_id')}`\n"
            msg += f"الحالة: {status}\n"
            msg += "-----------------------------------\n"
            
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"خطأ في جلب الفروع: {e}")

async def renew_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("يرجى كتابة الـ Client ID، مثال:\n`/renew 123456`", parse_mode="Markdown")
        return

    client_id = context.args[0]
    context.user_data['renew_client_id'] = client_id

    keyboard = [
        [
            InlineKeyboardButton("10 دقائق", callback_data="renew_10_دقيقة"),
            InlineKeyboardButton("ساعة", callback_data="renew_1_ساعة")
        ],
        [
            InlineKeyboardButton("يوم", callback_data="renew_1_يوم"),
            InlineKeyboardButton("أسبوع", callback_data="renew_1_أسبوع")
        ],
        [
            InlineKeyboardButton("شهر", callback_data="renew_1_شهر"),
            InlineKeyboardButton("3 شهور", callback_data="renew_3_شهر")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"اختر مدة التجديد للعميل `{client_id}`:", reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split('_')
    amount = int(data[1])
    unit = data[2]
    client_id = context.user_data.get('renew_client_id')

    if not client_id:
        await query.edit_message_text("حدث خطأ، اطلب الأمر مجدداً: /renew")
        return

    payload = {"client_id": client_id, "amount": amount, "unit": unit}

    try:
        res = requests.post(f"{SERVER_URL}/renew", json=payload, timeout=5)
        res_data = res.json()

        if res_data.get("status") == "success":
            await query.edit_message_text(
                f"✅ **تم التجديد بنجاح!**\n\n"
                f"🔑 العميل: `{client_id}`\n"
                f"➕ المضافة: {amount} {unit}\n"
                f"📅 الانتهاء الجديد: {res_data.get('new_expiry')}",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ فشلت عملية التجديد.")
    except Exception as e:
        await query.edit_message_text(f"خطأ: {e}")

def run_bot_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("branches", get_branches))
    bot_app.add_handler(CommandHandler("renew", renew_command))
    bot_app.add_handler(CallbackQueryHandler(button_handler))

    loop.run_until_complete(bot_app.initialize())
    loop.run_until_complete(bot_app.updater.start_polling(drop_pending_updates=True))
    loop.run_until_complete(bot_app.start())
    loop.run_forever()

# تشغيل البوت في Background Thread بـ Loop مستقل
threading.Thread(target=run_bot_loop, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
