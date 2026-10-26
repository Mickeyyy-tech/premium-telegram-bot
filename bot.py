import os
import asyncio
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
    ("@HackerxProoff", "https://t.me/HackerxProoff"),
    ("@HackerxService", "https://t.me/HackerxService"),
]

SUPPORT_URL = "https://t.me/Tspherez"

PACKAGES = {
    "Basic": (200, 3000),
    "Silver": (350, 5500),
    "Gold": (600, 12000),
    "Platinum": (900, 23000),
    "Diamond": (1200, 30000),
}

MENU = ReplyKeyboardMarkup(
    [
        ["MY SERVICES", "MY ACCOUNT"],
        ["BALANCE", "WITHDRAW"],
        ["REFER & EARN", "SUPPORT"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("JOIN CHANNEL 1", url=CHANNELS[0][1])],
        [InlineKeyboardButton("JOIN CHANNEL 2", url=CHANNELS[1][1])],
        [InlineKeyboardButton("VERIFY JOIN", callback_data="verify")],
    ]

    await update.message.reply_text(
        "Welcome!\n\n"
        "Bot use karne ke liye dono channels join karo. "
        "Uske baad VERIFY JOIN dabao.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    try:
        for channel, link in CHANNELS:
            member = await context.bot.get_chat_member(channel, user_id)

            if member.status not in ("member", "administrator", "creator"):
                await query.message.reply_text(
                    "Pehle dono channels join karo, phir VERIFY dabao."
                )
                return

        await query.message.reply_text(
            "Membership verified! Menu se option select karo.",
            reply_markup=MENU,
        )

    except Exception:
        await query.message.reply_text(
            "Membership check nahi ho paya. Channels join karke dobara try karo."
        )


async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []

    for name, (price, balance) in PACKAGES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{name} - Rs.{price} | Balance {balance:,}",
                callback_data=f"package:{name}",
            )
        ])

    await update.message.reply_text(
        "SELECT YOUR PLAN\n\nApna package choose karo:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def package_selected(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    name = query.data.split(":", 1)[1]

    if name not in PACKAGES:
        await query.message.reply_text("Invalid package.")
        return

    price, balance = PACKAGES[name]
    context.user_data["selected_package"] = name

    await query.message.reply_text(
        f"Package: {name}\n"
        f"Price: Rs.{price}\n"
        f"Displayed balance: {balance:,}\n\n"
        "Payment QR aur payment instructions ke liye support se contact karo.\n"
        "Payment verify hone tak order pending rahega.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "CONTACT SUPPORT",
                    url=SUPPORT_URL,
                )
            ]
        ]),
    )


async def utr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_utr"] = True

    await update.message.reply_text(
        "Apne payment ka UTR/transaction reference bhejo.\n"
        "Admin payment verify karega. Sirf UTR payment ka proof nahi hai."
    )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user = update.effective_user

    if context.user_data.get("awaiting_utr"):
        context.user_data["awaiting_utr"] = False

        package = context.user_data.get("selected_package", "Not selected")

        await update.message.reply_text(
            "Payment request submit ho gayi hai. "
            "Payment verify hone tak order pending rahega.",
            reply_markup=MENU,
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "PAYMENT REVIEW REQUEST\n\n"
                f"Name: {user.full_name}\n"
                f"Username: @{user.username or 'not set'}\n"
                f"User ID: {user.id}\n"
                f"Package: {package}\n"
                f"Submitted reference: {text}\n\n"
                "Payment account mein transaction check karein."
            ),
        )
        return

    if text == "MY SERVICES":
        await services(update, context)

    elif text == "MY ACCOUNT":
        await update.message.reply_text(
            f"Your account\nName: {user.full_name}\nID: {user.id}",
            reply_markup=MENU,
        )

    elif text == "BALANCE":
        await update.message.reply_text(
            "Package display balance aur actual withdrawable funds alag ho sakte hain.",
            reply_markup=MENU,
        )

    elif text == "WITHDRAW":
        await update.message.reply_text(
            "Withdrawal ke liye support se contact karo.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "SUPPORT",
                        url=SUPPORT_URL,
                    )
                ]
            ]),
        )

    elif text == "REFER & EARN":
        bot = await context.bot.get_me()
        await update.message.reply_text(
            f"Referral link:\nhttps://t.me/{bot.username}?start={user.id}\n\n"
            "Referral rewards abhi automatically calculate nahi hote.",
            reply_markup=MENU,
        )

    elif text == "SUPPORT":
        await update.message.reply_text(
            "Support ke liye neeche click karo.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "CONTACT SUPPORT",
                        url=SUPPORT_URL,
                    )
                ]
            ]),
        )


async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Admin only.")
        return

    await update.message.reply_text(
        "ADMIN HELP\n\n"
        "Payment requests manually verify karein.\n"
        "Approve karne se pehle apne payment account mein transaction check karein.\n"
        "Is version mein automatic approval ya approve/reject buttons nahi hain."
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("utr", utr_command))
    app.add_handler(CommandHandler("adminhelp", admin_help))

    app.add_handler(
        CallbackQueryHandler(verify, pattern="^verify$")
    )

    app.add_handler(
        CallbackQueryHandler(package_selected, pattern=r"^package:")
    )

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)
    )

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()
