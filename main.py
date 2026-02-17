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
