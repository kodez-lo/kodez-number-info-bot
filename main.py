#!/usr/bin/env python3
import os
import logging
import phonenumbers
from phonenumbers import geocoder, carrier, timezone

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("kodez-number-info-bot")

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6260666281")

PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID", "-1004453913171")
PRIVATE_CHANNEL_LINK = "https://t.me/+UMYdxsrFwXUwMzVl"

PUBLIC_CHANNEL_USERNAME = os.getenv("PUBLIC_CHANNEL_USERNAME", "@kodez0")
PUBLIC_CHANNEL_LINK = "https://t.me/kodez0"

YOUTUBE_LINK = "https://youtube.com/@kodez_lo?si=7YetsAD5q_ubVQyt"


def menu():
    return ReplyKeyboardMarkup(
        [["📱 Get Number Info"], ["❓ Help", "ℹ️ About"]],
        resize_keyboard=True,
        is_persistent=True,
    )


def join_buttons(private_pending=True, public_pending=True):
    rows = []
    if private_pending:
        rows.append([InlineKeyboardButton("✨ Join Channel 1", url=PRIVATE_CHANNEL_LINK)])
    if public_pending:
        rows.append([InlineKeyboardButton("🚀 Join Channel 2", url=PUBLIC_CHANNEL_LINK)])
    rows.append([InlineKeyboardButton("✅ I've Joined — Verify", callback_data="verify_join")])
    return InlineKeyboardMarkup(rows)


async def check_member(context, user_id, chat_id):
    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        }
    except Exception as e:
        log.warning("Membership check failed for %s: %s", chat_id, e)
        return False


async def get_membership(context, user_id):
    private_ok = await check_member(context, user_id, PRIVATE_CHANNEL_ID)
    public_ok = await check_member(context, user_id, PUBLIC_CHANNEL_USERNAME)
    return private_ok, public_ok


async def require_join(update, context):
    user = update.effective_user
    if not user:
        return False

    private_ok, public_ok = await get_membership(context, user.id)
    if private_ok and public_ok:
        return True

    pending = []
    if not private_ok:
        pending.append("❌ Channel 1 is still pending.")
    if not public_ok:
        pending.append("❌ Channel 2 is still pending.")

    txt = (
        "🔒 <b>Join Required</b>\n\n"
        + "\n".join(pending)
        + "\n\nJoin both channels and tap <b>I've Joined — Verify</b>."
    )

    markup = join_buttons(not private_ok, not public_ok)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                txt, parse_mode=ParseMode.HTML, reply_markup=markup
            )
        except Exception:
            pass
    else:
        await update.effective_message.reply_text(
            txt, parse_mode=ParseMode.HTML, reply_markup=markup
        )
    return False


async def notify_admin(update, context):
    if not ADMIN_CHAT_ID:
        return
    user = update.effective_user
    if not user:
        return
    username = f"@{user.username}" if user.username else "Not set"
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                "🆕 <b>New Bot Start</b>\n\n"
                f"👤 Name: {user.full_name}\n"
                f"🔗 Username: {username}\n"
                f"🆔 Telegram ID: <code>{user.id}</code>"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        log.warning("Admin notification failed: %s", e)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await notify_admin(update, context)

    await update.message.reply_text(
        "📱 <b>NUMBER INFO BOT</b>\n\n"
        "Send a 10-digit mobile number to get available public number information.\n\n"
        f"▶️ <b>YouTube:</b> {YOUTUBE_LINK}\n"
        f"📢 <b>Telegram:</b> {PUBLIC_CHANNEL_LINK}\n\n"
        "🚀 <b>Bot by Krishna Kodez</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=menu(),
        disable_web_page_preview=True,
    )

    await require_join(update, context)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ <b>Help</b>\n\n"
        "1. Join both required Telegram channels.\n"
        "2. Send a valid 10-digit Indian mobile number.\n"
        "3. The bot shows basic public number metadata when available.\n\n"
        "Example: <code>9876543210</code>\n\n"
        f"▶️ YouTube: {YOUTUBE_LINK}\n"
        f"📢 Telegram: {PUBLIC_CHANNEL_LINK}\n\n"
        "🚀 Bot by Krishna Kodez",
        parse_mode=ParseMode.HTML,
        reply_markup=menu(),
        disable_web_page_preview=True,
    )


async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ <b>About</b>\n\n"
        "NUMBER INFO BOT provides basic public phone-number metadata such as "
        "format, region, carrier metadata and timezone when available.\n\n"
        "It does not expose private subscriber records.\n\n"
        "🚀 <b>Bot by Krishna Kodez</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=menu(),
    )


async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await require_join(update, context):
        await q.edit_message_text(
            "✅ <b>Access Granted!</b>\n"
            "You can now send a 10-digit mobile number.",
            parse_mode=ParseMode.HTML,
        )


def parse_number(text):
    raw = text.strip().replace(" ", "").replace("-", "")
    if raw.startswith("+91"):
        raw = raw[3:]
    elif raw.startswith("91") and len(raw) == 12:
        raw = raw[2:]

    if not raw.isdigit() or len(raw) != 10:
        return None

    try:
        num = phonenumbers.parse("+91" + raw, None)
        if not phonenumbers.is_possible_number(num):
            return None
        return num
    except phonenumbers.NumberParseException:
        return None


def render_info(num):
    international = phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )
    national = phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.NATIONAL
    )
    region = geocoder.description_for_number(num, "en") or "Not available"
    provider = carrier.name_for_number(num, "en") or "Not available"
    zones = timezone.time_zones_for_number(num)
    tz = ", ".join(zones) if zones else "Not available"
    valid = "Yes" if phonenumbers.is_valid_number(num) else "No"

    return (
        "📱 <b>Number Information</b>\n\n"
        f"📞 <b>Number:</b> <code>{international}</code>\n"
        f"🏷 <b>National Format:</b> <code>{national}</code>\n"
        f"✅ <b>Valid Number:</b> {valid}\n"
        f"📍 <b>Region:</b> {region}\n"
        f"🌐 <b>Carrier Metadata:</b> {provider}\n"
        f"🕒 <b>Time Zone:</b> {tz}\n\n"
        "━━━━━━━━━━━━━━\n"
        "🚀 <b>Bot by Krishna Kodez</b>"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()

    if txt == "📱 Get Number Info":
        if await require_join(update, context):
            await update.message.reply_text("📲 Send a valid 10-digit mobile number.")
        return

    if txt == "❓ Help":
        await help_cmd(update, context)
        return

    if txt == "ℹ️ About":
        await about_cmd(update, context)
        return

    if not await require_join(update, context):
        return

    num = parse_number(txt)
    if not num:
        await update.message.reply_text(
            "⚠️ <b>Invalid Number</b>\nPlease send a valid 10-digit mobile number.",
            parse_mode=ParseMode.HTML,
        )
        return

    msg = await update.message.reply_text(
        "🔎 <b>Fetching available information...</b>",
        parse_mode=ParseMode.HTML,
    )
    await msg.edit_text(render_info(num), parse_mode=ParseMode.HTML)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about_cmd))
    app.add_handler(CallbackQueryHandler(verify_join, pattern="^verify_join$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🚀 Krishna Kodez NUMBER INFO BOT is running!", flush=True)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
