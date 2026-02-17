import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# --- Configurations ---
TOKEN = "8529724118:AAFxU42k6oBZq5Fd_09o7jcXGnFnLf2ANNw"
MONGO_URI = "mongodb+srv://phyohtetaung1091_db_user:EhJoxfniB6uFq9OA@cluster0.nrja3ig.mongodb.net/?appName=Cluster0"

# Database Connection with SSL Fix
client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.get_database('YeeSarSharDB')

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Functions ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # ပထမဆုံး ကျား/မ ရွေးခိုင်းမည်
    kb = [
        [InlineKeyboardButton("👨 ယောက်ျားလေး", callback_data="set_male"),
         InlineKeyboardButton("👩 မိန်းကလေး", callback_data="set_female")]
    ]
    await update.message.reply_text(
        f"မင်္ဂလာပါ {user.first_name} 🙏\nမြန်မာ LeoMatch Clone မှ ကြိုဆိုပါတယ်။\n\nရှေ့ဆက်ရန် သင့်ရဲ့ လိင်အမျိုးအစားကို အရင်ရွေးချယ်ပေးပါ-",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    # ကျား/မ သတ်မှတ်ခြင်း
    if query.data.startswith("set_"):
        gender = "male" if query.data == "set_male" else "female"
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"gender": gender, "name": query.from_user.first_name, "username": query.from_user.username}},
            upsert=True
        )
        
        # Gender ပြီးလျှင် Location တောင်းမည်
        await query.edit_message_text("✅ မှတ်သားပြီးပါပြီ။ အနီးနားကလူတွေကို ရှာဖွေနိုင်ဖို့ သင့်တည်နေရာကို ပေးပို့ပေးပါဦး။")
        
        loc_kb = [[KeyboardButton("📍 တည်နေရာပေးပို့ရန်", request_location=True)]]
        await context.bot.send_message(
            chat_id=user_id,
            text="အောက်ကခလုတ်ကို နှိပ်ပြီး Location Share ပေးပါ-",
            reply_markup=ReplyKeyboardMarkup(loc_kb, resize_keyboard=True, one_time_keyboard=True)
        )

    # Like ပေးသည့်အခါ
    elif query.data.startswith("like_"):
        await query.edit_message_text(text="✅ သင် Like ပေးလိုက်တာကို တစ်ဖက်လူဆီ အကြောင်းကြားပေးပါမယ်။")
    
    # Next (ကျော်ရန်)
    elif query.data == "next":
        await query.delete_message()
        # နောက်တစ်ယောက်ကို အလိုအလျောက် ထပ်ရှာပေးရန် find_match ကို ပြန်ခေါ်နိုင်သည် (optional)

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    user_id = update.effective_user.id
    
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
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

    if not user_data or 'gender' not in user_data or 'location' not in user_data:
        await update.message.reply_text("အရင်ဆုံး /start ကိုနှိပ်ပြီး အချက်အလက်တွေ အကုန်ဖြည့်ပေးပါဦး။")
        return

    user_coords = user_data['location']['coordinates']
    # ကိုယ်က male ဆိုရင် female ကိုရှာမယ်၊ female ဆိုရင် male ကိုရှာမယ်
    target_gender = "female" if user_data['gender'] == "male" else "male"
    
    # အကွာအဝေး အဆင့်ဆင့်ချဲ့ရှာခြင်း (၁၀ မိုင် -> ၅၀ မိုင် -> တစ်နိုင်ငံလုံး)
    search_distances = [16000, 80000, 800000]
    near_users = []
    current_dist_label = ""

    for dist in search_distances:
        near_users = await db.users.find({
            "location": {
                "$near": {
                    "$geometry": {"type": "Point", "coordinates": user_coords},
                    "$maxDistance": dist
                }
            },
            "user_id": {"$ne": user_id},
            "gender": target_gender
        }).to_list(length=5)
        
        if near_users:
            current_dist_label = "၁၀ မိုင်အတွင်း" if dist == 16000 else "မိုင် ၅၀ အတွင်း" if dist == 80000 else "တစ်နိုင်ငံလုံးအတိုင်းအတာ"
            break

    if not near_users:
        target_text = "မိန်းကလေး" if target_gender == "female" else "ယောက်ျားလေး"
        await update.message.reply_text(f"စိတ်မရှိပါနဲ့၊ လောလောဆယ် သင့်အနီးနားမှာ {target_text} အသစ် မတွေ့သေးပါဘူး။")
        return

    for target in near_users:
        target_name = target.get('name', 'အမည်မသိ')
        target_username = target.get('username')
        username_text = f"@{target_username}" if target_username else "Username မသိပါ"
        
        display_text = (
            f"👤 အမည်: {target_name}\n"
            f"🔗 Username: {username_text}\n"
            f"📍 {current_dist_label}မှာ ရှိနေပါတယ်။"
        )
        
        kb = [
            [InlineKeyboardButton("💚 Like", callback_data=f"like_{target['user_id']}"),
             InlineKeyboardButton("👎 Next", callback_data="next")]
        ]
        await update.message.reply_text(display_text, reply_markup=InlineKeyboardMarkup(kb))

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("find", find_match))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("LeoMatch Final Version is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
