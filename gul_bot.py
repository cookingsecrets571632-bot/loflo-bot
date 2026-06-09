import logging
from datetime import datetime
from telegram import (
    Update, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler,
)

# =============================================
BOT_TOKEN    = "8774639906:AAGgFzCz7OIXFeMKSJKFLvI3OGTuE8RnMhE"
CHANNEL_ID   = "@LoFlo_Xorazm"
ADMIN_ID     = 552774752
KARTA_RAQAM  = "9860 1201 7946 6285"
# =============================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RASM, NARX, TELEFON, JOYLASHUV, CHEK = range(5)
user_data_store = {}
active_ads = {}
pending_payments = {}


def format_caption(data, sotildi=False, daqiqa=None):
    base = (
        "🌸 *GUL SOTILADI!*\n\n"
        f"💰 *Narx:* {data['narx']}\n"
        f"📞 *Telefon:* {data['telefon']}\n"
        f"📍 *Joylashuv:* {data['joylashuv']}\n\n"
    )
    if sotildi:
        return base + f"✅ *SOTILDI!* ⏱ {daqiqa} daqiqada sotildi!"
    return base + "📩 Sotib olish uchun telefon raqamga murojaat qiling!"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌸 *LoFlo ga Xush Kelibsiz!*\n\n"
        "Gullaringizni tez va oson soting yoki arzon narxda gul sotib oling!\n\n"
        "📢 E'lon berish: /elon\n"
        "📋 Aktiv e'lonlarim: /elonlarim",
        parse_mode="Markdown"
    )


async def elon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 *1-qadam: Gul rasmi*\n\nGulning rasmini yuboring:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return RASM


async def rasm_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid] = {"photo_id": update.message.photo[-1].file_id}
    await update.message.reply_text(
        "✅ Rasm qabul qilindi!\n\n💰 *2-qadam: Narx*\n\nNarxini kiriting:",
        parse_mode="Markdown"
    )
    return NARX


async def narx_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid]["narx"] = update.message.text
    await update.message.reply_text(
        "✅ Narx qabul qilindi!\n\n📞 *3-qadam: Telefon*\n\nTelefon raqamingizni kiriting:",
        parse_mode="Markdown"
    )
    return TELEFON


async def telefon_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid]["telefon"] = update.message.text
    await update.message.reply_text(
        "✅ Telefon qabul qilindi!\n\n📍 *4-qadam: Joylashuv*\n\nQayerda turasiz?",
        parse_mode="Markdown"
    )
    return JOYLASHUV


async def joylashuv_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid]["joylashuv"] = update.message.text
    user_data_store[uid]["owner_id"] = uid
    user_data_store[uid]["vaqt"] = datetime.now()

    await update.message.reply_text(
        f"✅ Ma'lumotlar qabul qilindi!\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"💳 *TO'LOV*\n\n"
        f"E'lon narxi: *20 000 so'm*\n"
        f"Karta raqami:\n`{KARTA_RAQAM}`\n\n"
        f"📌 To'lovni amalga oshirib, *chek rasmini* yuboring.\n"
        f"━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
    return CHEK


async def chek_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id

    if not update.message.photo:
        await update.message.reply_text(
            "❗ Iltimos, chek *rasmini* yuboring.",
            parse_mode="Markdown"
        )
        return CHEK

    chek_photo_id = update.message.photo[-1].file_id
    ad_data = user_data_store.get(uid, {})
    ad_data["chek_photo_id"] = chek_photo_id
    pending_payments[uid] = ad_data

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{uid}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{uid}"),
        ]
    ])

    user = update.message.from_user
    username = f"@{user.username}" if user.username else user.full_name

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=chek_photo_id,
        caption=(
            f"💳 *Yangi to'lov cheki*\n\n"
            f"👤 {username} (`{uid}`)\n"
            f"💰 {ad_data.get('narx','—')}\n"
            f"📞 {ad_data.get('telefon','—')}\n"
            f"📍 {ad_data.get('joylashuv','—')}\n\n"
            f"Tasdiqlaysizmi?"
        ),
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    await update.message.reply_text(
        "⏳ *Chek adminga yuborildi!*\n\n"
        "5-15 daqiqa ichida tasdiqlanadi. 🌸",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

    user_data_store.pop(uid, None)
    return ConversationHandler.END


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    parts = query.data.split("_", 1)
    action, uid_str = parts[0], parts[1]
    uid = int(uid_str)
    ad = pending_payments.get(uid)

    if not ad:
        await query.edit_message_caption(
            caption="⚠️ Bu so'rov allaqachon ko'rib chiqilgan.",
            parse_mode="Markdown"
        )
        return

    if action == "approve":
        try:
            # Kanalga tugmasiz e'lon chiqarish
            sent = await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=ad["photo_id"],
                caption=format_caption(ad),
                parse_mode="Markdown"
                # tugma YO'Q — kanalda ko'rinmaydi
            )
            active_ads[sent.message_id] = {**ad, "sotildi": False}

            # Faqat sotuvchiga botda "Sotildi" tugmasi yuborish
            sotildi_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Sotildi!", callback_data=f"sotildi_{uid}_{sent.message_id}")]
            ])
            await context.bot.send_message(
                chat_id=uid,
                text=(
                    "🎉 *To'lovingiz tasdiqlandi!*\n\n"
                    "E'loningiz @LoFlo_Xorazm kanalga chiqarildi! 🌸\n\n"
                    "Gul sotilganda quyidagi tugmani bosing 👇"
                ),
                parse_mode="Markdown",
                reply_markup=sotildi_keyboard
            )

            await query.edit_message_caption(
                caption="✅ *Tasdiqlandi* — E'lon kanalga chiqarildi.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Xato: {e}")

    elif action == "reject":
        await context.bot.send_message(
            chat_id=uid,
            text=(
                "❌ *To'lovingiz tasdiqlanmadi.*\n\n"
                "Qayta /elon buyrug'ini yuboring."
            ),
            parse_mode="Markdown"
        )
        await query.edit_message_caption(
            caption="❌ *Rad etildi.*",
            parse_mode="Markdown"
        )

    pending_payments.pop(uid, None)


async def sotildi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    owner_id = int(parts[1])
    msg_id = int(parts[2])

    if query.from_user.id != owner_id:
        await query.answer("❌ Faqat e'lon egasi bosishi mumkin!", show_alert=True)
        return

    if msg_id not in active_ads or active_ads[msg_id]["sotildi"]:
        await query.answer("Bu e'lon allaqachon sotilgan!", show_alert=True)
        return

    ad = active_ads[msg_id]
    daqiqa = max(1, int((datetime.now() - ad["vaqt"]).total_seconds() // 60))

    # Kanalda e'lonni "Sotildi" ga o'zgartirish
    await context.bot.edit_message_caption(
        chat_id=CHANNEL_ID,
        message_id=msg_id,
        caption=format_caption(ad, sotildi=True, daqiqa=daqiqa),
        parse_mode="Markdown"
    )
    active_ads[msg_id]["sotildi"] = True

    # Sotuvchiga tabrik
    await query.edit_message_text(
        text=f"✅ *Tabriklaymiz!*\n\nGul *{daqiqa} daqiqada* sotildi! 🌸",
        parse_mode="Markdown"
    )


async def elonlarim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    my_ads = {
        mid: ad for mid, ad in active_ads.items()
        if ad["owner_id"] == uid and not ad["sotildi"]
    }

    if not my_ads:
        await update.message.reply_text("📭 Sizda aktiv e'lonlar yo'q.")
        return

    for mid, ad in my_ads.items():
        daqiqa = int((datetime.now() - ad["vaqt"]).total_seconds() // 60)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sotildi!", callback_data=f"sotildi_{uid}_{mid}")]
        ])
        await update.message.reply_text(
            f"🌸 *E'lon*\n"
            f"💰 {ad['narx']}\n"
            f"📍 {ad['joylashuv']}\n"
            f"⏱ {daqiqa} daqiqa oldin",
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store.pop(uid, None)
    await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("elon", elon_start)],
        states={
            RASM:      [MessageHandler(filters.PHOTO, rasm_olish)],
            NARX:      [MessageHandler(filters.TEXT & ~filters.COMMAND, narx_olish)],
            TELEFON:   [MessageHandler(filters.TEXT & ~filters.COMMAND, telefon_olish)],
            JOYLASHUV: [MessageHandler(filters.TEXT & ~filters.COMMAND, joylashuv_olish)],
            CHEK:      [MessageHandler(filters.PHOTO, chek_olish),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, chek_olish)],
        },
        fallbacks=[CommandHandler("bekor", bekor)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("elonlarim", elonlarim))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^(approve|reject)_"))
    app.add_handler(CallbackQueryHandler(sotildi_callback, pattern=r"^sotildi_"))

    print("✅ LoFlo bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
