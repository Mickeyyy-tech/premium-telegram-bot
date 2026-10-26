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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = 8596715964

CHANNELS = [
    ("@HackerxProoff", "https://t.me/HackerxProoff"),
    ("@HackerxService", "https://t.me/HackerxService"),
]
SUPPORT_URL = "https://t.me/Tspherez"

# Upload your QR image into the same GitHub repository as bot.py
# and keep this exact filename, or change it to match your uploaded filename.
QR_FILE = "file_00000000ca5082109a05b096a996b6cd.jpg"

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

# In-memory order tracking: pending orders reset if the worker restarts.
# Always verify the actual payment in your payment account before approving.
pending_orders = {}
approved_users = set()
admin_waiting_for_details = {}  # admin_id -> customer user_id


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_utr"] = False
    keyboard = [
        [InlineKeyboardButton("JOIN CHANNEL 1", url=CHANNELS[0][1])],
        [InlineKeyboardButton("JOIN CHANNEL 2", url=CHANNELS[1][1])],
        [InlineKeyboardButton("VERIFY JOIN", callback_data="verify")],
    ]
    await update.message.reply_text(
        "Welcome!\n\nBot use karne ke liye dono channels join karo. "
        "Uske baad VERIFY JOIN dabao.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try:
        for channel, _link in CHANNELS:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status not in ("member", "administrator", "creator"):
                await query.message.reply_text(
                    "Pehle dono channels join karo, phir VERIFY JOIN dabao."
                )
                return
        await query.message.reply_text(
            "Membership verified! Menu se option select karo.",
            reply_markup=MENU,
        )
    except Exception:
        logging.exception("Channel membership check failed")
        await query.message.reply_text(
            "Membership check nahi ho paya. Channels join karke dobara try karo."
        )


async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for name, (price, balance) in PACKAGES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{name} - ₹{price} | Balance {balance:,}",
                callback_data=f"package:{name}",
            )
        ])
    await update.message.reply_text(
        "SELECT YOUR PLAN\n\nApna package choose karo:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    name = query.data.split(":", 1)[1]
    if name not in PACKAGES:
        await query.message.reply_text("Invalid package.")
        return

    price, balance = PACKAGES[name]
    context.user_data["selected_package"] = name
    context.user_data["awaiting_utr"] = False

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 SUBMIT UTR", callback_data="submit_utr")],
        [InlineKeyboardButton("CONTACT SUPPORT", url=SUPPORT_URL)],
    ])
    caption = (
        f"📦 Package: {name}\n"
        f"💰 Price: ₹{price}\n"
        f"Displayed balance: {balance:,}\n\n"
        "1. QR par payment karein.\n"
        "2. Payment account mein transaction successful hone ke baad "
        "SUBMIT UTR dabayein.\n"
        "3. Admin payment manually verify karega.\n\n"
        "⚠️ UTR dene se payment automatically verify nahi hoti."
    )
    if os.path.isfile(QR_FILE):
        with open(QR_FILE, "rb") as photo:
            await query.message.reply_photo(
                photo=photo,
                caption=caption,
                reply_markup=keyboard,
            )
    else:
        await query.message.reply_text(
            caption + f"\n\nQR image file nahi mili: {QR_FILE}\n"
            "QR image ko bot.py ke saath repository ke root mein upload karein.",
            reply_markup=keyboard,
        )


async def submit_utr_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not context.user_data.get("selected_package"):
        await query.message.reply_text("Pehle MY SERVICES se package select karo.")
        return
    context.user_data["awaiting_utr"] = True
    await query.message.reply_text(
        "Ab apna UTR / transaction reference number ek message mein bhejo.\n"
        "Payment verify hone tak order pending rahega."
    )


async def utr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("selected_package"):
        await update.message.reply_text("Pehle MY SERVICES se package select karo.")
        return
    context.user_data["awaiting_utr"] = True
    await update.message.reply_text("Apna UTR / transaction reference number bhejo.")


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user = update.effective_user

    # Admin's next message after /senddetails is sent privately to that customer.
    if user.id == ADMIN_ID and ADMIN_ID in admin_waiting_for_details:
        customer_id = admin_waiting_for_details.pop(ADMIN_ID)
        try:
            await context.bot.send_message(
                chat_id=customer_id,
                text="📩 Your details from admin:\n\n" + text,
            )
            await update.message.reply_text(f"Details customer {customer_id} ko bhej di gayi.")
        except Exception:
            logging.exception("Could not send details")
            await update.message.reply_text(
                "Details nahi bhej paya. Customer ne bot start kiya hai ya nahi, check karein."
            )
        return

    if context.user_data.get("awaiting_utr"):
        context.user_data["awaiting_utr"] = False
        package = context.user_data.get("selected_package")
        if package not in PACKAGES:
            await update.message.reply_text("Pehle package select karo.")
            return
        price, balance = PACKAGES[package]
        order_key = f"{user.id}:{update.message.message_id}"
        pending_orders[order_key] = {
            "user_id": user.id,
            "name": user.full_name,
            "username": user.username or "not set",
            "package": package,
            "price": price,
            "balance": balance,
            "utr": text,
            "status": "pending",
        }
        admin_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve:{order_key}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject:{order_key}"),
        ]])
        await update.message.reply_text(
            "UTR submit ho gaya. Payment verify hone tak order pending hai.",
            reply_markup=MENU,
        )
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "🧾 PAYMENT REVIEW REQUEST\n\n"
                    f"Name: {user.full_name}\n"
                    f"Username: @{user.username or 'not set'}\n"
                    f"User ID: {user.id}\n"
                    f"Package: {package}\n"
                    f"Amount: ₹{price}\n"
                    f"Submitted UTR: {text}\n\n"
                    "Payment account mein transaction check karein before approval."
                ),
                reply_markup=admin_keyboard,
            )
        except Exception:
            logging.exception("Could not notify admin")
            await update.message.reply_text(
                "Admin ko notify nahi kar paya. Support se contact karo."
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
            "Package par dikhaya gaya balance sirf displayed balance hai; "
            "ye apne aap withdrawable cash nahi hai.",
            reply_markup=MENU,
        )
    elif text == "WITHDRAW":
        await update.message.reply_text(
            "Support se contact karein for help.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("SUPPORT", url=SUPPORT_URL)
            ]]),
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
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("CONTACT SUPPORT", url=SUPPORT_URL)
            ]]),
        )


async def review_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("Admin only.")
        return

    action, order_key = query.data.split(":", 1)
    order = pending_orders.get(order_key)
    if not order:
        await query.message.reply_text(
            "Order memory mein nahi mila. Worker restart hua ho sakta hai; "
            "payment account se verify karein aur customer ko manually contact karein."
        )
        return
    if order["status"] != "pending":
        await query.message.reply_text(f"Order already {order['status']}.")
        return

    if action == "approve":
        order["status"] = "approved"
        approved_users.add(order["user_id"])
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "✅ Payment approved!\n\n"
                f"Package: {order['package']}\n"
                "Admin aapki details manually bot par bhejega. "
                "Kripya intezar karein."
            ),
        )
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"Order approved. Details bhejne ke liye:\n/senddetails {order['user_id']}"
        )
    elif action == "reject":
        order["status"] = "rejected"
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "❌ Payment approve nahi hui. Apne payment transaction ko check karein "
                "aur support se contact karein agar aapko lagta hai ki ye galti hai."
            ),
        )
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Order rejected; customer ko notify kar diya.")


async def senddetails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Admin only.")
        return
    if not context.args:
        await update.message.reply_text(
            "Use: /senddetails USER_ID\nExample: /senddetails 123456789"
        )
        return
    try:
        customer_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("USER_ID number hona chahiye.")
        return
    if customer_id not in approved_users:
        await update.message.reply_text(
            "Is worker session mein is customer ka approved order record nahi mila. "
            "Pehle payment approval check karein."
        )
        return
    admin_waiting_for_details[ADMIN_ID] = customer_id
    await update.message.reply_text(
        f"Customer {customer_id} ko bhejne ke liye ab apna next message bhejo. "
        "Wahi message customer ko privately chala jayega."
    )


async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Admin only.")
        return
    await update.message.reply_text(
        "ADMIN COMMANDS\n\n"
        "/adminhelp - commands list\n"
        "/senddetails USER_ID - approved customer ko next message manually bhejein\n\n"
        "Approve se pehle payment account mein transaction verify karein.\n"
        "Important: pending orders and approvals are stored in memory only and may reset "
        "when Render restarts the worker."
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("utr", utr_command))
    app.add_handler(CommandHandler("adminhelp", admin_help))
    app.add_handler(CommandHandler("senddetails", senddetails_command))
    app.add_handler(CallbackQueryHandler(verify, pattern=r"^verify$"))
    app.add_handler(CallbackQueryHandler(package_selected, pattern=r"^package:"))
    app.add_handler(CallbackQueryHandler(submit_utr_button, pattern=r"^submit_utr$"))
    app.add_handler(CallbackQueryHandler(review_order, pattern=r"^(approve|reject):"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
