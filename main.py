import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from motor.motor_asyncio import AsyncIOMotorClient
import certifi
from flask import Flask
from threading import Thread
import os

# --- Flask Server (UptimeRobot အတွက်) ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Configurations ---
TOKEN = "8529724118:AAFxU42k6oBZq5Fd_09o7jcXGnFnLf2ANNw"
MONGO_URI = "mongodb+srv://phyohtetaung1091_db_user:EhJoxfniB6uFq9OA@cluster0.nrja3ig.mongodb.net/?appName=Cluster0"

# Join ခိုင်းမည့် Channel IDs (Username များ)
CHANNELS = ["@titokvideodowloader", "@musicdowloader"]

client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.get_database('YeeSarSharDB')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Check Join Function ---
async def is_user_joined(context, user_id):
    for channel in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

# --- Keyboards ---
def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔍 လူရှာရန်")],
        [KeyboardButton("📍 တည်နေရာအသစ်ပို့ရန်", request_location=True)],
        [KeyboardButton("👤 My Profile")]
    ], resize_keyboard=True)

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    joined = await is_user_joined(context, user_id)
    
    if not joined:
        keyboard = [
            [InlineKeyboardButton("1️⃣ Join TikTok Downloader", url="https://t.me/titokvideodowloader")],
            [InlineKeyboardButton("2️⃣ Join Music Downloader", url="https://t.me/musicdowloader")],
            [InlineKeyboardButton("✅ Join ပြီးပါပြီ", callback_data="check_join")]
        ]
        await update.message.reply_text(
            "⚠️ Bot ကို အသုံးမပြုမီ ကျွန်ုပ်တို့၏ Channel (၂) ခုလုံးကို အရင် Join ပေးရပါမယ်။\nJoin ပြီးမှ '✅ Join ပြီးပါပြီ' ကို နှိပ်ပါ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Join ပြီးသားဖြစ်ပါက Gender ရွေးခိုင်းမည်
    kb = [[InlineKeyboardButton("👨 ယောက်ျားလေး", callback_data="set_male"),
           InlineKeyboardButton("👩 မိန်းကလေး", callback_data="set_female")]]
    await update.message.reply_text(
        f"မင်္ဂလာပါ {update.effective_user.first_name} 🙏\nဆက်လက်လုပ်ဆောင်ရန် သင့်လိင်အမျိုးအစားကို ရွေးချယ်ပေးပါ-",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "check_join":
        if await is_user_joined(context, user_id):
            await query.edit_message_text("✅ ကျေးဇူးတင်ပါတယ်။ အခု Bot ကို စတင်အသုံးပြုနိုင်ပါပြီ။ /start ကို ပြန်နှိပ်ပေးပါ။")
        else:
            await query.answer("❌ Channel အားလုံးကို Join ဖို့ လိုအပ်ပါသေးတယ်!", show_alert=True)

    elif query.data.startswith("set_"):
        gender = "male" if query.data == "set_male" else "female"
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"gender": gender, "name": query.from_user.first_name, "username": query.from_user.username}},
            upsert=True
        )
        await query.edit_message_text("✅ မှတ်သားပြီးပါပြီ။ အနီးနားကလူတွေကို ရှာဖွေနိုင်ဖို့ သင့်တည်နေရာ (Location) ကို ပေးပို့ပေးပါ။")
        loc_kb = [[KeyboardButton("📍 တည်နေရာပေးပို့ရန်", request_location=True)]]
        await context.bot.send_message(chat_id=user_id, text="အောက်ကခလုတ်ကို နှိပ်ပါ-", reply_markup=ReplyKeyboardMarkup(loc_kb, resize_keyboard=True, one_time_keyboard=True))

    elif query.data.startswith("like_"):
        target_id = int(query.data.split("_")[1])
        try:
            await context.bot.send_message(chat_id=target_id, text="🔔 တစ်ယောက်ယောက်က သင့်ကို Like ပေးလိုက်ပါတယ်။ /find ကိုနှိပ်ပြီး ပြန်ရှာကြည့်ပါ!")
        except: pass
        await query.edit_message_text(text="✅ သင် Like ပေးလိုက်တာကို တစ်ဖက်လူဆီ အကြောင်းကြားပေးပါမယ်။")

    elif query.data == "next":
        await query.delete_message()
        await find_match(update, context)

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_joined(context, user_id): return
    
    loc = update.message.location
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"location": {"type": "Point", "coordinates": [loc.longitude, loc.latitude]}}},
        upsert=True
    )
    await update.message.reply_text("✅ အကုန်လုံး အဆင်သင့်ဖြစ်ပါပြီ။", reply_markup=main_menu_keyboard())

async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_joined(context, user_id):
        await update.message.reply_text("Channel များကို အရင် Join ပါ။ /start")
        return

    user_data = await db.users.find_one({"user_id": user_id})
    if not user_data or 'gender' not in user_data or 'location' not in user_data:
        await update.message.reply_text("အရင်ဆုံး /start ကိုနှိပ်ပြီး Profile ဖြည့်ပေးပါ။")
        return

    user_coords = user_data['location']['coordinates']
    target_gender = "female" if user_data['gender'] == "male" else "male"
    
    cursor = db.users.aggregate([
        {"$geoNear": {
            "near": {"type": "Point", "coordinates": user_coords},
            "distanceField": "dist.calculated",
            "query": {"user_id": {"$ne": user_id}, "gender": target_gender},
            "spherical": True
        }},
        {"$sample": {"size": 1}}
    ])
    results = await cursor.to_list(length=1)
    
    if not results:
        await update.message.reply_text("လောလောဆယ် လူအသစ်မရှိသေးပါဘူး။")
        return

    found_user = results[0]
    display_text = f"👤 အမည်: {found_user.get('name')}\n🔗 Username: @{found_user.get('username', 'N/A')}\n📍 အနီးနားမှာ ရှိနေပါတယ်။"
    kb = [[InlineKeyboardButton("💚 Like", callback_data=f"like_{found_user['user_id']}"),
           InlineKeyboardButton("👎 Next", callback_data="next")]]
    
    await context.bot.send_message(chat_id=user_id, text=display_text, reply_markup=InlineKeyboardMarkup(kb))

def main():
    keep_alive() # UptimeRobot အတွက်
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^🔍 လူရှာရန်$"), find_match))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("LeoMatch with Force Join is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
