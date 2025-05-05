from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from twilio.rest import Client
from keep_alive import keep_alive
from datetime import timedelta
import time
import logging

logging.basicConfig(level=logging.INFO)

# Admin and permission system
ADMIN_IDS = [6165060012]
user_permissions = {6165060012: float("inf")}
user_used_free_plan = set()

# Twilio session data
user_clients = {}
user_available_numbers = {}
user_purchased_numbers = {}

def permission_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        expire_time = user_permissions.get(user_id, 0)
        if time.time() > expire_time:
            keyboard = [
                [InlineKeyboardButton("1 Hour - $FREE", callback_data="PLAN:1h")],
                [InlineKeyboardButton("1 Day - $2", callback_data="PLAN:1d")],
                [InlineKeyboardButton("7 Day - $10", callback_data="PLAN:7d")],
                [InlineKeyboardButton("15 Day - $15", callback_data="PLAN:15d")],
                [InlineKeyboardButton("30 Day - $20", callback_data="PLAN:30d")],
            ]
            await (update.message or update.callback_query).reply_text(
                "Bot এর Subscription কিনার জন্য নিচের বাটনে ক্লিক করুন:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        return await func(update, context)
    return wrapper

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "স্বাগতম Evan Bot-এ 🌸!\n\n"
        "/login <SID> <TOKEN>\n"
        "/buy_number <Area Code>\n"
        "/show_messages\n"
        "/delete_number\n"
        "/my_numbers\n"
        "SUPPORT : @EVANHELPING_BOT"
    )

async def grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ আপনি এই কমান্ড ব্যবহার করতে পারবেন না।")
        return
    if len(context.args) != 2:
        await update.message.reply_text("ব্যবহার: /grant <user_id> <duration> (যেমন 3d)")
        return
    try:
        target_id = int(context.args[0])
        duration = context.args[1].lower()
        if duration.endswith("mo"):
            seconds = int(duration[:-2]) * 2592000
        else:
            unit_map = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
            unit = duration[-1]
            amount = int(duration[:-1])
            seconds = amount * unit_map[unit]
        user_permissions[target_id] = time.time() + seconds
        await update.message.reply_text(f"✅ {target_id} কে {duration} সময়ের জন্য পারমিশন দেওয়া হয়েছে।")
    except:
        await update.message.reply_text("❌ ভুল ফরম্যাট। ব্যবহার করুন m, h, d, w, mo")

@permission_required
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("ব্যবহার: /login <SID> <AUTH_TOKEN>")
        return
    sid, token = context.args
    try:
        client = Client(sid, token)
        client.api.accounts(sid).fetch()
        user_clients[update.effective_user.id] = client
        await update.message.reply_text("✅ লগইন সফল!")
    except Exception as e:
        logging.exception("Login error:")
        await update.message.reply_text(f"লগইন ব্যর্থ: {e}")

@permission_required
async def buy_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("ব্যবহার: /buy_number <Area Code>")
        return
    user_id = update.effective_user.id
    client = user_clients.get(user_id)
    if not client:
        await update.message.reply_text("⚠️ আগে /login করুন।")
        return
    try:
        numbers = client.available_phone_numbers("CA").local.list(area_code=context.args[0], limit=10)
        if not numbers:
            await update.message.reply_text("নাম্বার পাওয়া যায়নি।")
            return
        user_available_numbers[user_id] = [n.phone_number for n in numbers]
        keyboard = [[InlineKeyboardButton(n.phone_number, callback_data=f"BUY:{n.phone_number}")] for n in numbers]
        keyboard.append([InlineKeyboardButton("Cancel ❌", callback_data="CANCEL")])
        await update.message.reply_text(
            "নিচের নাম্বারগুলো পাওয়া গেছে:\n\n" + "\n".join(user_available_numbers[user_id]),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.exception("Buy number error:")
        await update.message.reply_text(f"সমস্যা: {e}")

@permission_required
async def show_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = user_clients.get(update.effective_user.id)
    if not client:
        await update.message.reply_text("⚠️ আগে /login করুন।")
        return
    try:
        msgs = client.messages.list(limit=20)
        incoming = [msg for msg in msgs if msg.direction == "inbound"]
        if not incoming:
            await update.message.reply_text("কোনো Incoming Message পাওয়া যায়নি।")
            return
        output = "\n\n".join([f"From: {m.from_}\nTo: {m.to}\nBody: {m.body}" for m in incoming[:5]])
        await update.message.reply_text(output)
    except Exception as e:
        logging.exception("Show messages error:")
        await update.message.reply_text(f"সমস্যা: {e}")

@permission_required
async def delete_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = user_clients.get(update.effective_user.id)
    if not client:
        await update.message.reply_text("⚠️ আগে /login করুন।")
        return
    try:
        numbers = client.incoming_phone_numbers.list(limit=1)
        if not numbers:
            await update.message.reply_text("নাম্বার খুঁজে পাওয়া যায়নি।")
            return
        numbers[0].delete()
        await update.message.reply_text("✅ নাম্বার ডিলিট হয়েছে।")
    except Exception as e:
        logging.exception("Delete number error:")
        await update.message.reply_text(f"ডিলিট করতে সমস্যা: {e}")

@permission_required
async def my_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = user_clients.get(update.effective_user.id)
    if not client:
        await update.message.reply_text("⚠️ আগে /login করুন।")
        return
    try:
        numbers = client.incoming_phone_numbers.list()
        if not numbers:
            await update.message.reply_text("আপনার কোনো নাম্বার নেই।")
            return
        keyboard = [[InlineKeyboardButton(n.phone_number, callback_data=f"DELETE:{n.phone_number}")] for n in numbers]
        await update.message.reply_text("আপনার নাম্বারগুলো:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logging.exception("My numbers error:")
        await update.message.reply_text(f"সমস্যা: {e}")

# NEW: List permitted users command
async def permitted_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ আপনি এই কমান্ড ব্যবহার করতে পারবেন না।")
        return

    if not user_permissions:
        await update.message.reply_text("কোনো ইউজার এখনো পারমিশন নেয়নি।")
        return

    msg = "✅ List Of Permitted Users ✅\n\n"
    now = time.time()
    for uid, expire_time in user_permissions.items():
        if expire_time == float("inf"):
            duration = "Unlimited"
        else:
            remaining = max(0, expire_time - now)
            duration = str(timedelta(seconds=int(remaining)))

        try:
            user = await context.bot.get_chat(uid)
            name = user.full_name
            username = f"@{user.username}" if user.username else "N/A"
        except:
            name = "Unknown"
            username = "N/A"

        msg += (
            f"👤 User Name: {name}\n"
            f"🆔 User ID: {uid}\n"
            f"🔗 Username: {username}\n"
            f"⏳ Duration Left: {duration}\n\n"
        )

    await update.message.reply_text(msg)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("BUY:"):
        number = data.split("BUY:")[1]
        client = user_clients.get(user_id)
        if not client:
            await query.edit_message_text("⚠️ আগে /login করুন।")
            return
        try:
            purchased = client.incoming_phone_numbers.create(phone_number=number)
            user_purchased_numbers.setdefault(user_id, []).append(purchased.phone_number)
            await query.edit_message_text(f"✅ আপনি নাম্বারটি কিনেছেন: {purchased.phone_number}")
        except Exception as e:
            logging.exception("Buy via button error:")
            await query.edit_message_text(f"নাম্বার কেনা যায়নি: {e}")

    elif data.startswith("DELETE:"):
        number = data.split("DELETE:")[1]
        client = user_clients.get(user_id)
        try:
            nums = client.incoming_phone_numbers.list(phone_number=number)
            if nums:
                nums[0].delete()
                await query.edit_message_text(f"✅ নাম্বার {number} ডিলিট হয়েছে।")
            else:
                await query.edit_message_text("নাম্বার পাওয়া যায়নি।")
        except Exception as e:
            logging.exception("Delete via button error:")
            await query.edit_message_text(f"নাম্বার ডিলিট করতে সমস্যা: {e}")

    elif data == "CANCEL":
        await query.edit_message_text("নাম্বার নির্বাচন বাতিল করা হয়েছে।")

    elif data.startswith("PLAN:"):
        plan = data.split(":")[1]
        username = f"@{query.from_user.username}" if query.from_user.username else "N/A"
        prices = {
            "1h": (3600, "1 Hour", "$FREE"),
            "1d": (86400, "1 Day", "$2"),
            "7d": (604800, "7 Day", "$10"),
            "15d": (1296000, "15 Day", "$15"),
            "30d": (2592000, "30 Day", "$20")
        }
        if plan == "1h":
            if user_id in user_used_free_plan:
                await query.edit_message_text("আপনি ইতিমধ্যেই ফ্রি প্লান ব্যবহার করেছেন।")
                return
            user_used_free_plan.add(user_id)
            user_permissions[user_id] = time.time() + 3600
            await query.edit_message_text("✅ আপনি ১ ঘন্টার জন্য ফ্রি প্লান একটিভ করেছেন।")
            return

        if plan in prices:
            seconds, label, cost = prices[plan]
            msg = (
                f"Please send {cost} to Binance Pay ID: 469628989\n\n"
                f"পেমেন্ট করার পর প্রুভ হিসাবে (screenshot/transaction ID) Admin কে পাঠিয়ে দিন\n\n"
                f"Your payment details:\n"
                f"🆔 User ID: {user_id}\n"
                f"👤 Username: {username}\n"
                f"📋 Plan: {label} - {cost}\n"
                f"💰 Amount: {cost}\n\n"
                f"Verification must be completed within 15 minutes, or the request will be cancelled."
            )
            await query.edit_message_text(msg)

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ আপনি এই কমান্ড ব্যবহার করতে পারবেন না।")
        return
    if not context.args:
        await update.message.reply_text("ব্যবহার: /add_admin <user_id>")
        return
    try:
        new_admin_id = int(context.args[0])
        if new_admin_id in ADMIN_IDS:
            await update.message.reply_text("এই ইউজার ইতিমধ্যে Admin।")
            return
        ADMIN_IDS.append(new_admin_id)
        user_permissions[new_admin_id] = float("inf")
        await update.message.reply_text(f"✅ {new_admin_id} এখন Admin!")
    except ValueError:
        await update.message.reply_text("❌ সঠিকভাবে user_id দিন।")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ আপনি এই কমান্ড ব্যবহার করতে পারবেন না।")
        return
    if not context.args:
        await update.message.reply_text("ব্যবহার: /remove_admin <user_id>")
        return
    try:
        target_id = int(context.args[0])
        if target_id == user_id:
            await update.message.reply_text("❌ আপনি নিজেকে Admin থেকে সরাতে পারবেন না।")
            return
        if target_id not in ADMIN_IDS:
            await update.message.reply_text("❌ এই ইউজার Admin না।")
            return
        if len(ADMIN_IDS) <= 1:
            await update.message.reply_text("❌ কমপক্ষে ১ জন Admin থাকা আবশ্যক।")
            return
        ADMIN_IDS.remove(target_id)
        user_permissions.pop(target_id, None)
        await update.message.reply_text(f"✅ {target_id} কে Admin থেকে সরানো হয়েছে।")
    except ValueError:
        await update.message.reply_text("❌ সঠিকভাবে user_id দিন।")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ আপনি এই কমান্ড ব্যবহার করতে পারবেন না।")
        return
    text = "বর্তমান অ্যাডমিনদের তালিকা:\n\n"
    for admin_id in ADMIN_IDS:
        try:
            user = await context.bot.get_chat(admin_id)
            name = user.full_name
            username = f"@{user.username}" if user.username else "N/A"
        except:
            name = "Unknown"
            username = "N/A"
        text += f"🆔 {admin_id} — {name} ({username})\n"
    await update.message.reply_text(text)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ আপনি এই কমান্ড ব্যবহার করতে পারবেন না।")
        return
    if not context.args:
        await update.message.reply_text("ব্যবহার: /broadcast <message>")
        return
    text = " ".join(context.args)
    success = fail = 0
    for uid in user_permissions:
        try:
            await context.bot.send_message(chat_id=uid, text=text)
            success += 1
        except:
            fail += 1
    await update.message.reply_text(f"✅ পাঠানো হয়েছে: {success} জনকে\n❌ ব্যর্থ হয়েছে: {fail} জনকে")

def main():
    keep_alive()
    TOKEN = "7253583924:AAENVbdYNjHdbKHV0SJhnhoomyeOM2YeLXc"
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("grant", grant))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("buy_number", buy_number))
    app.add_handler(CommandHandler("show_messages", show_messages))
    app.add_handler(CommandHandler("delete_number", delete_number))
    app.add_handler(CommandHandler("my_numbers", my_numbers))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("add_admin", add_admin))
    app.add_handler(CommandHandler("remove_admin", remove_admin))
    app.add_handler(CommandHandler("list_admins", list_admins))
    app.add_handler(CommandHandler("permitted_users", permitted_users))  # <- New handler
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
