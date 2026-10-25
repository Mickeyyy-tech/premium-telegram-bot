import os
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = 8596715964

CHANNELS = [
    "@HackerxProoff",
    "@HackerxService",
]

SUPPORT = "https://t.me/Tspherez"

PACKAGES = {
    "Basic": (200, "3,000"),
    "Silver": (350, "5,500"),
    "Gold": (600, "12,000"),
    "Platinum": (900, "23,000"),
    "Diamond": (1200, "30,000"),
}

MENU = [
    ["🔹 MY SERVICES", "👤 MY ACCOUNT"],
    ["💰 BALANCE", "💸 WITHDRAW"],
    ["🎁 REFER & EARN", "🆘 SUPPORT"],
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(
            "🔵 JOIN CHANNEL 1",
            url="https://t.me/HackerxProoff"
        )],
        [InlineKeyboardButton(
            "🔵 JOIN CHANNEL 2",
            url="https://t.me/HackerxService"
        )],
        [InlineKeyboardButton("🟢 VERIFY ✅", callback_data="verify")],
    ]

    await update.message.reply_text(
        "💎 WELCOME TO PREMIUM SERVICES\n\n"
        "Bot use karne ke liye pehle dono channels join karein.\n"
        "Join karne ke baad VERIFY dabayein.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def is_member(context, user_id):
    for channel in CHANNELS:
        try:
            member = await context.bot.get_chat_member(
                chat_id=channel,
                user_id=user_id,
            )
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            return False
    return True


async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_member(context, query.from_user.id):
        await query.message.reply_text(
            "❌ Aapko dono channels join karne honge.\n"
            "Join karne ke baad VERIFY dobara dabayein."
        )
        return

    context.user_data["verified"] = True

    await query.message.reply_text(
        "✅ Verification successful!\n\nWelcome to the main menu.",
        reply_markup=ReplyKeyboardMarkup(
            MENU,
            resize_keyboard=True,
        ),
    )


async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = []

    for name, (price, balance) in PACKAGES.items():
        buttons.append([
            InlineKeyboardButton(
                f"{name} — ₹{price} | Balance {balance}",
                callback_data=f"package:{name}",
            )
        ])

    await update.message.reply_text(
        "💎 SELECT YOUR PACKAGE",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def package_selected(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    name = query.data.split(":", 1)[1]

    if name not in PACKAGES:
        return

    price, balance = PACKAGES[name]
    context.user_data["selected_package"] = name

    await query.message.reply_text(
        f"📦 Package: {name}\n"
        f"💳 Price: ₹{price}\n"
        f"💰 Display balance: {balance}\n\n"
        "Payment ke liye support se sampark karein.\n"
        "Payment confirm hone se pehle koi balance credit nahi hoga.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🆘 SUPPORT", url=SUPPORT)]
        ]),
    )


async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id
    text = update.message.text

    if not context.user_data.get("verified"):
        if not await is_member(context, user_id):
            await start(update, context)
            return
        context.user_data["verified"] = True

    if text == "🔹 MY SERVICES":
        await services(update, context)

    elif text == "👤 MY ACCOUNT":
        await update.message.reply_text(
            f"👤 Your account\nTelegram ID: {user_id}"
        )

    elif text == "💰 BALANCE":
        await update.message.reply_text(
            "💰 Balance payment verification ke baad update hoga."
        )

    elif text == "💸 WITHDRAW":
        await update.message.reply_text(
            "Withdrawal ke liye support se sampark karein.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🆘 SUPPORT", url=SUPPORT)]
            ]),
        )

    elif text == "🎁 REFER & EARN":
        bot = await context.bot.get_me()
        link = f"https://t.me/{bot.username}?start={user_id}"
        await update.message.reply_text(
            f"🎁 Your referral link:\n{link}"
        )

    elif text == "🆘 SUPPORT":
        await update.message.reply_text(
            "Support ke liye neeche click karein.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("CONTACT SUPPORT", url=SUPPORT)]
            ]),
        )

    elif context.user_data.get("awaiting_utr"):
        utr = text.strip()

        if not (8 <= len(utr) <= 40) or not utr.isalnum():
            await update.message.reply_text(
                "❌ UTR format sahi nahi hai. Dobara enter karein."
            )
            return

        package = context.user_data.get("selected_package", "Not selected")
        order_id = f"{user_id}-{update.message.message_id}"

        context.user_data["awaiting_utr"] = False

        await context.bot.send_message(
            ADMIN_ID,
            f"🧾 PAYMENT REVIEW REQUEST\n\n"
            f"Order: {order_id}\n"
            f"User ID: {user_id}\n"
            f"Package: {package}\n"
            f"UTR: {utr}\n\n"
            "Bank/payment provider mein payment verify karein."
        )

        await update.message.reply_text(
            "⏳ UTR admin ko bhej diya gaya hai.\n"
            "Payment verify hone tak order pending rahega."
        )


async def utr_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.user_data.get("selected_package"):
        await update.message.reply_text(
            "Pehle MY SERVICES se package select karein."
        )
        return

    context.user_data["awaiting_utr"] = True
    await update.message.reply_text(
        "Payment karne ke baad apna UTR number bhejein."
    )


async def admin_help(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only.")
        return

    await update.message.reply_text(
        "👑 ADMIN HELP\n\n"
        "/pendinginfo — Help\n"
        "Payment requests ko manually check karein.\n"
        "UTR milna payment successful hone ka proof nahi hai."
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("utr", utr_command))
    app.add_handler(CommandHandler("adminhelp", admin_help))
    app.add_handler(CallbackQueryHandler(verify, pattern="^verify$"))
    app.add_handler(
        CallbackQueryHandler(package_selected, pattern=r"^package:")
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
