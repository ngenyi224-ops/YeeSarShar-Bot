import logging
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from pymongo import MongoClient

# --- DATABASE CONNECTION (SSL Error ကင်းဝေးစေရန် အထူးပြင်ဆင်ထားသည်) ---
# tlsAllowInvalidCertificates=True ပါဝင်မှသာ Render တွင် အမှန်ခြစ်စာသား ပြန်ပို့နိုင်မည်ဖြစ်သည်
MONGO_URL = "mongodb+srv://phyohtetaung1091_db_user:EhJoxfniB6uFq9OA@cluster0.nrja3ig.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
client = MongoClient(MONGO_URL, tls=True, tlsAllowInvalidCertificates=True, connectTimeoutMS=30000)
db = client['YeeSarSharDB']
users_col = db['users']

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- HEALTH CHECK SERVER (Render Web Service အတွက် Port 10000) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Live!")

def run_health_server():
    # Render အတွက် Port 10000 ဖြစ်ရပါမည်
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- BOT STATES ---
GENDER, AGE, CITY, PHOTO = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
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
        users_col.update_one({"user_id": user.id}, {"$set": user_data}, upsert=True)
        # အမှန်ခြစ်စာသား ပေါ်လာစေရန် ဤနေရာတွင် ရေးသားထားသည်
        await update.message.reply_text(
            "✅ မှတ်ပုံတင်ပြီးပါပြီ!\n'🔍 ရှာဖွေမည်' ကို နှိပ်ပြီး လူရှာနိုင်ပါပြီ။",
            reply_markup=ReplyKeyboardMarkup([['🔍 ရှာဖွေမည်']], resize_keyboard=True)
        )
    except Exception as e:
        logging.error(f"DB Error: {e}")
        await update.message.reply_text("စနစ် ခေတ္တနှေးကွေးနေပါသည်။ ခဏအကြာမှ ပြန်စမ်းကြည့်ပါ။")
    return ConversationHandler.END

async def search_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_user = users_col.find_one({"user_id": user_id})
    seen = current_user.get("seen_users", []) if current_user else []
    query = {"user_id": {"$ne": user_id, "$nin": seen}}
    target = list(users_col.aggregate([{"$match": query}, {"$sample": {"size": 1}}]))
    
    if target:
        t = target[0]
        users_col.update_one({"user_id": user_id}, {"$push": {"seen_users": t['user_id']}})
        await update.message.reply_photo(photo=t['photo'], caption=f"👤 {t['name']}\n🎂 {t['age']}\n📍 {t['city']}", 
                                         reply_markup=ReplyKeyboardMarkup([['❤️ Like', '👎 Next']], resize_keyboard=True))
    else:
        users_col.update_one({"user_id": user_id}, {"$set": {"seen_users": []}})
        await update.message.reply_text("လောလောဆယ် လူကုန်သွားပါပြီ။")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # သင်ပေးထားသော Token အသစ်ကို ဤနေရာတွင် ထည့်သွင်းထားပါသည်
    TOKEN = "8529724118:AAFxU42k6oBZq5Fd_09o7jcXGnFnLf2ANNw"
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
        },
        fallbacks=[CommandHandler('start', start)],
    ))
    app.add_handler(MessageHandler(filters.Regex('^(🔍 ရှာဖွေမည်|❤️ Like|👎 Next)$'), search_people))
    
    logging.info("YeeSarShar Bot is starting with new token...")
    # Conflict Error (terminated by other request) ကို ရှင်းရန် drop_pending_updates=True ထည့်ထားသည်
    app.run_polling(drop_pending_updates=True)
