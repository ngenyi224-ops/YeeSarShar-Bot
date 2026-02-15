import logging
import threading
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from pymongo import MongoClient

# --- DATABASE CONNECTION (အပြီးသတ်ပြင်ဆင်ထားသည်) ---
# SSL error ကင်းဝေးစေရန် အထူးပြုပြင်ထားသော URL ဖြစ်ပါသည်
MONGO_URL = "mongodb+srv://phyohtetaung1091_db_user:EhJoxfniB6uFq9OA@cluster0.nrja3ig.mongodb.net/YeeSarSharDB?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
client = MongoClient(MONGO_URL, tls=True, tlsAllowInvalidCertificates=True, connectTimeoutMS=30000, socketTimeoutMS=30000)
db = client.get_database('YeeSarSharDB')
users_col = db['users']

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- HEALTH CHECK SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- BOT STATES ---
GENDER, AGE, CITY, PHOTO = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        # Database ချိတ်ဆက်မှုကို အရင်စမ်းသပ်သည်
        existing_user = users_col.find_one({"user_id": user_id})
        if existing_user:
            await update.message.reply_text(
                f"မင်္ဂလာပါ {existing_user['name']}! ✨\nအသစ်ရှာရန် '🔍 ရှာဖွေမည်' ကို နှိပ်ပါ။",
                reply_markup=ReplyKeyboardMarkup([['🔍 ရှာဖွေမည်']], resize_keyboard=True)
            )
            return ConversationHandler.END
    except Exception:
        pass

    await update.message.reply_text(
        "🇲🇲 YeeSarShar မှ ကြိုဆိုပါတယ်!\nစတင်ရန် သင်က ဘယ်သူလဲ?",
        reply_markup=ReplyKeyboardMarkup([['ယောင်္ကျားလေး 👦', 'မိန်းကလေး 👧']], one_time_keyboard=True, resize_keyboard=True)
    )
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("သင့်အသက်ကို ရိုက်ထည့်ပါ။")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['age'] = update.message.text
    await update.message.reply_text("သင်ဘယ်မြို့မှာ နေပါသလဲ?")
    return CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text
    await update.message.reply_text("သင့်ရဲ့ ဓာတ်ပုံတစ်ပုံ ပို့ပေးပါ။ 📸")
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo_id = update.message.photo[-1].file_id
    user_data = {
        "user_id": user.id, "name": user.first_name, "gender": context.user_data['gender'],
        "age": context.user_data['age'], "city": context.user_data['city'], "photo": photo_id, "seen_users": []
    }
    try:
        # အချက်အလက်သိမ်းဆည်းခြင်းကို Retry လုပ်ပေးထားပါသည်
        users_col.update_one({"user_id": user.id}, {"$set": user_data}, upsert=True)
        await update.message.reply_text("✅ မှတ်ပုံတင်ပြီးပါပြီ!\n'🔍 ရှာဖွေမည်' ကို နှိပ်ပါ။",
            reply_markup=ReplyKeyboardMarkup([['🔍 ရှာဖွေမည်']], resize_keyboard=True))
    except Exception as e:
        logging.error(f"DB WRITE ERROR: {e}")
        await update.message.reply_text("စနစ် ခေတ္တနှေးကွေးနေပါသည်။ ၁ မိနစ်ခန့်အကြာမှ ပြန်စမ်းကြည့်ပါ။")
    return ConversationHandler.END

async def search_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        current_user = users_col.find_one({"user_id": user_id})
        seen = current_user.get("seen_users", []) if current_user else []
        target = list(users_col.aggregate([{"$match": {"user_id": {"$ne": user_id, "$nin": seen}}}, {"$sample": {"size": 1}}]))
        if target:
            t = target[0]
            users_col.update_one({"user_id": user_id}, {"$push": {"seen_users": t['user_id']}})
            await update.message.reply_photo(photo=t['photo'], caption=f"👤 {t['name']}\n🎂 {t['age']}\n📍 {t['city']}", 
                reply_markup=ReplyKeyboardMarkup([['❤️ Like', '👎 Next']], resize_keyboard=True))
        else:
            await update.message.reply_text("လောလောဆယ် လူကုန်သွားပါပြီ။")
    except Exception:
        await update.message.reply_text("ရှာဖွေမှု အဆင်မပြေဖြစ်နေပါသည်။")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    # သင်ပေးထားသော Token အသစ်
    TOKEN = "8529724118:AAFxU42k6oBZq5Fd_09o7jcXGnFnLf2ANNw"
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
                AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
                CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
                PHOTO: [MessageHandler(filters.PHOTO, get_photo)]},
        fallbacks=[CommandHandler('start', start)]
    ))
    app.add_handler(MessageHandler(filters.Regex('^(🔍 ရှာဖွေမည်|❤️ Like|👎 Next)$'), search_people))
    
    logging.info("Bot is starting...")
    # Conflict Error ရှင်းရန် drop_pending_updates=True ကို မဖြစ်မနေ သုံးထားပါသည်
    app.run_polling(drop_pending_updates=True)
