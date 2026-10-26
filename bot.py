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
logging.getLogger("httpx").setLevel(logging.WARNING)

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
        [InlineKeyboardButton("✅ VERIFY JOIN", callback_data="verify")],
    ]

    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Bot use karne ke liye dono channels join karo, "
        "phir VERIFY JOIN dabao.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    try:
        for channel, _ in CHANNELS:
            member = await context.bot.get_chat_member(channel, user_id)

            if member.status not in ("member", "administrator", "creator"):
                await query.message.reply_text(
                    "❌ Pehle dono channels join karo, phir VERIFY dabao."
                )
                return

        await query.message.reply_text(
            "✅ Membership verified!\nMenu se option select karo.",
            reply_markup=MENU,
        )

    except Exception:
        await query.message.reply_text(
            "Membership check nahi ho paya. Dono channels join karke "
            "dobara try karo. Agar issue rahe, admin ko contact karo."
        )


async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []

    for name, (price, balance) in PACKAGES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{name} — ₹{price} | Display: {balance:,}",
                callback_data=f"package:{name}",
            )
        ])

    await update.message.reply_text(
        "💎 SELECT YOUR PACKAGE\n\n"
        "Package aur display balance choose karo:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def package_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
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
        f"📦 Package: {name}\n"
        f"💰 Price: ₹{price}\n"
        f"📊 Display balance: {balance:,}\n\n"
        "Payment QR ke liye support se contact karo.\n"
        "Payment verify hone se pehle order confirmed nahi hoga.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 CONTACT SUPPORT", url=SUPPORT_URL)]
        ]),
    )


async def utr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_utr"] = True
    await update.message.reply_text(
        "Apne payment ka UTR/transaction reference bhejo.\n"
    "UTR apne aap payment proof nahi hai; admin payment check karega."
