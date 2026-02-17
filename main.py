import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# --- Configurations ---
TOKEN = "8529724118:AAFxU42k6oBZq5Fd_09o7jcXGnFnLf2ANNw"
# SSL Error ကျော်ရန် certifi.where() ကို သုံးထားပါသည်
MONGO_URI = "mongodb+srv://phyohtetaung1091_db_user:EhJoxfniB6uFq9OA@cluster0.nrja3ig.mongodb.net/?appName=Cluster0"

# Database Connection
client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.get_database('YeeSarSharDB')

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Functions ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"မင်္ဂလာပါ {user.first_name} 🙏\n"
        "မြန်မာ LeoMatch Clone Bot မှ ကြိုဆိုပါတယ်။\n\n"
        "လူရှာဖွေနိုင်ဖို့ အောက်ကခလုတ်ကိုနှိပ်ပြီး သင့်တည်နေရာကို အရင်ပေးပို့ပါခင်ဗျာ။"
    )
    # Location တောင်းသည့် ခလုတ်
    kb = [[KeyboardButton("📍 တည်နေရာပေးပို့ရန်", request_location=True)]]
    await update.message.reply_text(welcome_text, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    user = update.effective_user
    
    # User အချက်အလက်နှင့် တည်နေရာကို Database တွင်သိမ်းဆည်းခြင်း
    await db.users.update_one(
        {"user_id": user.id},
        {"$set": {
            "name": user.first_name,
            "username": user.username,
            "location": {
                "type": "Point",
                "coordinates": [loc.longitude, loc.latitude]
            }
        }},
        upsert=True
    )
    await update.message.reply_text("✅ တည်နေရာမှတ်သားပြီးပါပြီ။ အခု /find ကိုနှိပ်ပြီး လူရှာနိုင်ပါပြီ။")

async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = await db.users.find_one({"user_id": user_id})

    if not user_data or 'location' not in user_data:
        await update.message.reply_text("အရင်ဆုံး တည်နေရာ (Location) ပေးပို့ပေးပါဦး။")
        return

    # ကိုယ့်ပတ်လည် ၁၀၀ ကီလိုမီတာအတွင်းကလူတွေကို ရှာဖွေခြင်း
    user_coords = user_data['location']['coordinates']
    near_users = await db.users.find({
        "location": {
            "$near": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": user_coords
                },
                "$maxDistance": 100000  # 100 KM
            }
        },
        "user_id": {"$ne": user_id}
    }).to_list(length=10)

    if not near_users:
        await update.message.reply_text("စိတ်မရှိပါနဲ့၊ အနီးနားမှာ လူအသစ်မတွေ့သေးပါဘူး။")
        return

    # တွေ့ရှိသူများကို တစ်ယောက်ချင်းစီ ပြသခြင်း
    for target in near_users:
        target_name = target.get('name', 'အမည်မသိ')
        target_username = target.get('username', 'username_မရှိပါ')
        
        text = f"👤 အမည်: {target_name}\n🔗 Username: @{target_username}\n📍 သင့်အနီးနားမှာ ရှိနေပါတယ်။"
        
        # Like/Next ခလုတ်များ
        keyboard = [
            [InlineKeyboardButton("💚 Like", callback_data=f"like_{target['user_id']}"),
             InlineKeyboardButton("👎 Next", callback_data="next")]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("like_"):
        target_id = query.data.split("_")[1]
        await query.edit_message_text(text="✅ သင် Like ပေးလိုက်တာကို တစ်ဖက်လူဆီ အကြောင်းကြားပေးပါမယ်။")
        # ဤနေရာတွင် တစ်ဖက်လူဆီသို့ Notification ပို့သည့် Logic ထည့်နိုင်ပါသည်
    elif query.data == "next":
        await query.delete_message()

# --- Main ---

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("find", find_match))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
