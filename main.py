import logging
import os
import certifi
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from pymongo import MongoClient

# 1. Database Setup (SSL Error အမြစ်ပြတ်ရှင်းရန်)
ca = certifi.where()
MONGO_URL = os.environ.get("MONGODB_URI")
client = MongoClient(MONGO_URL, tlsCAFile=ca, tlsAllowInvalidCertificates=True)
db = client.get_database('YeeSarSharDB')
users_col = db['users']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot အလုပ်လုပ်နေပါပြီ။ ဓာတ်ပုံပို့ကြည့်ပါ။")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        try:
            # ချိတ်ဆက်မှု ရှိမရှိ အရင်စမ်းမည်
            client.admin.command('ping') 
            await update.message.reply_text("✅ Database နှင့် ချိတ်ဆက်မှု အောင်မြင်ပါသည်။")
        except Exception as e:
            await update.message.reply_text(f"❌ DB Error: {str(e)}")

if __name__ == '__main__':
    TOKEN = "8529724118:AAFxU42k6oBZq5Fd_09o7jcXGnFnLf2ANNw"
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()
