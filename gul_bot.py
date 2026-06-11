import logging
import re
import io
import os
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont
from telegram import (
    Update, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler,
)

# =============================================
BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
CHANNEL_ID   = os.getenv("CHANNEL_ID", "@LoFlo_Xorazm")
ADMIN_ID     = int(os.getenv("ADMIN_ID", "552774752"))
KARTA_RAQAM  = os.getenv("KARTA_RAQAM", "9860 1201 7946 6285")
# =============================================

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Railway Variables ga qo'shing.")

# O'zbekiston vaqti UTC+5
UZ_TZ = timezone(timedelta(hours=5))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RASM1, RASM2, NARX, TELEFON, JOYLASHUV, CHEK = range(6)
user_data_store = {}
active_ads = {}
pending_payments = {}


def escape_md(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))


def add_watermark(photo_bytes):
    try:
        img = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        width, height = img.size
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        font_size_big   = max(56, width // 12) + 8
        font_size_small = max(40, width // 18) + 8

        sana = datetime.now(UZ_TZ).strftime("%d.%m.%y | %H:%M")

        try:
            font_big   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size_big)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size_small)
        except:
            font_big   = ImageFont.load_default()
            font_small = ImageFont.load_default()

        text1 = "LoFlo"
        text2 = "@LoFlo_Xorazm"
        text3 = sana

        bbox1 = draw.textbbox((0, 0), text1, font=font_big)
        bbox2 = draw.textbbox((0, 0), text2, font=font_small)
        bbox3 = draw.textbbox((0, 0), text3, font=font_small)

        w1 = bbox1[2] - bbox1[0]
        w2 = bbox2[2] - bbox2[0]
        w3 = bbox3[2] - bbox3[0]
        h1 = bbox1[3] - bbox1[1]
        h2 = bbox2[3] - bbox2[1]
        h3 = bbox3[3] - bbox3[1]

        padding = 24
        max_w   = max(w1, w2, w3) + padding * 2
        total_h = h1 + h2 + h3 + padding * 4

        x = width - max_w - 15
        y = 15

        draw.rounded_rectangle(
            [x - padding, y, x + max_w, y + total_h],
            radius=18,
            fill=(0, 0, 0, 170)
        )

        draw.text(
            (x + (max_w - w1) // 2 - padding, y + padding),
            text1, font=font_big, fill=(255, 255, 255, 255)
        )
        draw.text(
            (x + (max_w - w2) // 2 - padding, y + padding + h1 + padding // 2),
            text2, font=font_small, fill=(237, 147, 177, 255)
        )
        draw.text(
            (x + (max_w - w3) // 2 - padding, y + padding + h1 + h2 + padding),
            text3, font=font_small, fill=(200, 200, 200, 220)
        )

        result = Image.alpha_composite(img, overlay).convert("RGB")
        output = io.BytesIO()
        result.save(output, format="JPEG", quality=95)
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Watermark xato: {e}")
        return io.BytesIO(photo_bytes)


def format_caption(data, sotildi=False, daqiqa=None):
    narx      = escape_md(data['narx'])
    telefon   = escape_md(data['telefon'])
    joylashuv = escape_md(data['joylashuv'])
    base = (
        "🌸 *GUL SOTILADI\!*\n\n"
        f"💰 *Narx:* {narx}\n"
        f"📞 *Telefon:* {telefon}\n"
        f"📍 *Joylashuv:* {joylashuv}\n\n"
    )
    if sotildi:
        return base + f"✅ *SOTILDI\!* ⏱ {daqiqa} daqiqada sotildi\!"
    return base + "📩 Sotib olish uchun telefon raqamga murojaat qiling\!"


def format_caption_sotildi(data, daqiqa):
    narx      = escape_md(data['narx'])
    joylashuv = escape_md(data['joylashuv'])
    return (
        "🌸 *GUL SOTILADI\!*\n\n"
        f"💰 *Narx:* {narx}\n"
        f"📞 *Telefon:* 🔒 _Raqam yashirildi_\n"
        f"📍 *Joylashuv:* {joylashuv}\n\n"
        f"✅ *SOTILDI\!* ⏱ {daqiqa} daqiqada sotildi\!"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌸 *LoFlo ga Xush Kelibsiz\!*\n\n"
        "Gullaringizni tez va oson soting yoki arzon narxda gul sotib oling\!\n\n"
        "📢 E'lon berish: /elon\n"
        "📋 Aktiv e'lonlarim: /elonlarim",
        parse_mode="MarkdownV2"
    )


async def elon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 *1\\-qadam: Birinchi rasm*\n\nGulning *birinchi rasmini* yuboring:",
        parse_mode="MarkdownV2",
        reply_markup=ReplyKeyboardRemove()
    )
    return RASM1


async def rasm1_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    photo_bytes = await photo_file.download_as_bytearray()
    watermarked = add_watermark(bytes(photo_bytes))
    msg = await update.message.reply_photo(
        photo=watermarked,
        caption="✅ 1\\-rasm qabul qilindi\\!",
        parse_mode="MarkdownV2"
    )
    user_data_store[uid] = {"photo_id1": msg.photo[-1].file_id}
    await update.message.reply_text(
        "📸 *2\\-qadam: Ikkinchi rasm*\n\nGulning *ikkinchi rasmini* yuboring:",
        parse_mode="MarkdownV2"
    )
    return RASM2


async def rasm2_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    photo_bytes = await photo_file.download_as_bytearray()
    watermarked = add_watermark(bytes(photo_bytes))
    msg = await update.message.reply_photo(
        photo=watermarked,
        caption="✅ 2\\-rasm qabul qilindi\\!",
        parse_mode="MarkdownV2"
    )
    user_data_store[uid]["photo_id2"] = msg.photo[-1].file_id
    await update.message.reply_text(
        "✅ Ikkala rasm qabul qilindi\\!\n\n💰 *3\\-qadam: Narx*\n\nNarxini kiriting:",
        parse_mode="MarkdownV2"
    )
    return NARX


async def narx_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid]["narx"] = update.message.text
    await update.message.reply_text(
        "✅ Narx qabul qilindi\\!\n\n📞 *4\\-qadam: Telefon*\n\nTelefon raqamingizni kiriting:",
        parse_mode="MarkdownV2"
    )
    return TELEFON


async def telefon_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid]["telefon"] = update.message.text
    await update.message.reply_text(
        "✅ Telefon qabul qilindi\\!\n\n📍 *5\\-qadam: Joylashuv*\n\nQayerda turasiz?",
        parse_mode="MarkdownV2"
    )
    return JOYLASHUV


async def joylashuv_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid]["joylashuv"] = update.message.text
    user_data_store[uid]["owner_id"] = uid
    user_data_store[uid]["vaqt"] = datetime.now(UZ_TZ)
    karta = escape_md(KARTA_RAQAM)
    await update.message.reply_text(
        f"✅ Ma'lumotlar qabul qilindi\\!\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"💳 *TO'LOV*\n\n"
        f"E'lon narxi: *20 000 so'm*\n"
        f"Karta raqami:\n`{karta}`\n\n"
        f"📌 To'lovni amalga oshirib, *chek rasmini* yuboring\\.\n"
        f"━━━━━━━━━━━━━━━━━",
        parse_mode="MarkdownV2"
    )
    return CHEK


async def chek_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not update.message.photo:
        await update.message.reply_text("❗ Iltimos, chek rasmini yuboring\\.", parse_mode="MarkdownV2")
        return CHEK

    chek_photo_id = update.message.photo[-1].file_id
    ad_data = user_data_store.get(uid, {})
    ad_data["chek_photo_id"] = chek_photo_id
    pending_payments[uid] = ad_data

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{uid}"),
        InlineKeyboardButton("❌ Rad etish",  callback_data=f"reject_{uid}"),
    ]])

    user     = update.message.from_user
    username = f"@{user.username}" if user.username else user.full_name

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=chek_photo_id,
        caption=(
            f"💳 Yangi to'lov cheki\n\n"
            f"👤 {username} ({uid})\n"
            f"💰 {ad_data.get('narx','—')}\n"
            f"📞 {ad_data.get('telefon','—')}\n"
            f"📍 {ad_data.get('joylashuv','—')}\n\n"
            f"Tasdiqlaysizmi?"
        ),
        reply_markup=keyboard
    )

    await update.message.reply_text(
        "⏳ Chek adminga yuborildi\\!\n\n5\\-15 daqiqa ichida tasdiqlanadi\\. 🌸",
        parse_mode="MarkdownV2",
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

    parts      = query.data.split("_", 1)
    action     = parts[0]
    uid        = int(parts[1])
    ad         = pending_payments.get(uid)

    if not ad:
        await query.edit_message_caption(caption="⚠️ Bu so'rov allaqachon ko'rib chiqilgan.")
        return

    if action == "approve":
        try:
            media = [
                InputMediaPhoto(
                    media=ad["photo_id1"],
                    caption=format_caption(ad),
                    parse_mode="MarkdownV2"
                ),
                InputMediaPhoto(media=ad["photo_id2"])
            ]
            sent_messages = await context.bot.send_media_group(
                chat_id=CHANNEL_ID,
                media=media
            )
            msg_id = sent_messages[0].message_id
            active_ads[msg_id] = {**ad, "sotildi": False}

            sotildi_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Sotildi!", callback_data=f"sotildi_{uid}_{msg_id}")
            ]])
            await context.bot.send_message(
                chat_id=uid,
                text=(
                    "🎉 To'lovingiz tasdiqlandi\\!\n\n"
                    "E'loningiz @LoFlo\\_Xorazm kanalga chiqarildi\\! 🌸\n\n"
                    "Gul sotilganda quyidagi tugmani bosing 👇"
                ),
                parse_mode="MarkdownV2",
                reply_markup=sotildi_keyboard
            )
            await query.edit_message_caption(caption="✅ Tasdiqlandi — E'lon kanalga chiqarildi.")
        except Exception as e:
            logger.error(f"Xato: {e}")

    elif action == "reject":
        await context.bot.send_message(
            chat_id=uid,
            text="❌ To'lovingiz tasdiqlanmadi\\.\n\nQayta /elon buyrug'ini yuboring\\.",
            parse_mode="MarkdownV2"
        )
        await query.edit_message_caption(caption="❌ Rad etildi.")

    pending_payments.pop(uid, None)


async def sotildi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts    = query.data.split("_")
    owner_id = int(parts[1])
    msg_id   = int(parts[2])

    if query.from_user.id != owner_id:
        await query.answer("❌ Faqat e'lon egasi bosishi mumkin!", show_alert=True)
        return

    if msg_id not in active_ads or active_ads[msg_id]["sotildi"]:
        await query.answer("Bu e'lon allaqachon sotilgan!", show_alert=True)
        return

    ad     = active_ads[msg_id]
    daqiqa = max(1, int((datetime.now(UZ_TZ) - ad["vaqt"]).total_seconds() // 60))

    await context.bot.edit_message_caption(
        chat_id=CHANNEL_ID,
        message_id=msg_id,
        caption=format_caption_sotildi(ad, daqiqa),
        parse_mode="MarkdownV2"
    )
    active_ads[msg_id]["sotildi"] = True

    await query.edit_message_text(
        text=f"✅ Tabriklaymiz\\!\n\nGul *{daqiqa}* daqiqada sotildi\\! 🌸",
        parse_mode="MarkdownV2"
    )


async def elonlarim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid    = update.message.from_user.id
    my_ads = {
        mid: ad for mid, ad in active_ads.items()
        if ad["owner_id"] == uid and not ad["sotildi"]
    }
    if not my_ads:
        await update.message.reply_text("📭 Sizda aktiv e'lonlar yo'q.")
        return

    for mid, ad in my_ads.items():
        daqiqa   = int((datetime.now(UZ_TZ) - ad["vaqt"]).total_seconds() // 60)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Sotildi!", callback_data=f"sotildi_{uid}_{mid}")
        ]])
        await update.message.reply_text(
            f"🌸 *E'lon*\n"
            f"💰 {escape_md(ad['narx'])}\n"
            f"📍 {escape_md(ad['joylashuv'])}\n"
            f"⏱ {daqiqa} daqiqa oldin",
            parse_mode="MarkdownV2",
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
            RASM1:     [MessageHandler(filters.PHOTO, rasm1_olish)],
            RASM2:     [MessageHandler(filters.PHOTO, rasm2_olish)],
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
