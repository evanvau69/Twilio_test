from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from twilio.rest import Client
from keep_alive import keep_alive
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import random
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
from datetime import timedelta
import time
import logging
import asyncio

logging.basicConfig(level=logging.INFO)

# Admin system
ADMIN_IDS = [6165060012]
user_permissions = {6165060012: float("inf")}
user_used_free_plan = set()

# Twilio session
user_clients = {}
user_available_numbers = {}
user_purchased_numbers = {}

# Permission check decorator
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
                "Bot ржПрж░ Subscription ржХрж┐ржирж╛рж░ ржЬржирзНржп ржирж┐ржЪрзЗрж░ ржмрж╛ржЯржирзЗ ржХрзНрж▓рж┐ржХ ржХрж░рзБржи:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        return await func(update, context)
    return wrapper

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "рж╕рзНржмрж╛ржЧрждржо Evan Bot-ржП ЁЯМ╕ ржХрж╛ржЬ ржХрж░рж╛рж░ ржЬржирзНржп ржирж┐ржЪрзЗрж░ ржХржорж╛ржирзНржб ржЧрзБрж▓рзЛ ржмрзНржпржмрж╣рж╛рж░ ржХрж░рждрзЗ ржкрж╛рж░рзЗржи!\n\n"
        "/login <SID> <TOKEN>\n"
        "/buy_number <Area Code>\n"
        "/show_messages\n"
        "/delete_number\n"
        "/my_numbers\n"
        "SUPPORT : @EVANHELPING_BOT"
    )

# Admin permission grant
async def grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("тЭМ ржЖржкржирж┐ ржПржЗ ржХржорж╛ржирзНржб ржмрзНржпржмрж╣рж╛рж░ ржХрж░рждрзЗ ржкрж╛рж░ржмрзЗржи ржирж╛ред")
        return
    if len(context.args) != 2:
        await update.message.reply_text("ржмрзНржпржмрж╣рж╛рж░: /grant <user_id> <duration> (ржпрзЗржоржи 3d)")
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
        await update.message.reply_text(f"тЬЕ {target_id} ржХрзЗ {duration} рж╕ржорзЯрзЗрж░ ржЬржирзНржп ржкрж╛рж░ржорж┐рж╢ржи ржжрзЗржУрзЯрж╛ рж╣рзЯрзЗржЫрзЗред")
    except:
        await update.message.reply_text("тЭМ ржнрзБрж▓ ржлрж░ржорзНржпрж╛ржЯред ржмрзНржпржмрж╣рж╛рж░ ржХрж░рзБржи m, h, d, w, mo")

# Active user list
async def active_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("тЭМ ржЖржкржирж┐ ржПржЗ ржХржорж╛ржирзНржб ржмрзНржпржмрж╣рж╛рж░ ржХрж░рждрзЗ ржкрж╛рж░ржмрзЗржи ржирж╛ред")
        return
    now = time.time()
    active = {uid: exp for uid, exp in user_permissions.items() if exp > now or exp == float("inf")}
    if not active:
        await update.message.reply_text("ржХрзЛржирзЛ Active Permission ржЗржЙржЬрж╛рж░ ржирзЗржЗред")
        return

    msg = "тЬЕ Active Permission ржЗржЙржЬрж╛рж░ рж▓рж┐рж╕рзНржЯ тЬЕ\n\n"
    for uid, exp in active.items():
        try:
            user = await context.bot.get_chat(uid)
            name = user.full_name
            username = f"@{user.username}" if user.username else "N/A"
        except:
            name = "Unknown"
            username = "N/A"

        duration = "Unlimited" if exp == float("inf") else str(timedelta(seconds=int(exp - now)))
        msg += (
            f"ЁЯСд Name: {name}\n"
            f"ЁЯЖФ ID: {uid}\n"
            f"ЁЯФЧ Username: {username}\n"
            f"тП│ Time Left: {duration}\n\n"
        )
    await update.message.reply_text(msg)

# Canadian area codes list (example, you can add more)
canadian_area_codes = [
    '416', '647', '905', '613', '519', '438', '514', '403', '204', '306',
    '705', '902', '778', '587', '250', '604', '819', '807', '905', '819', '905'
]

# This function will send the daily message with 3 random area codes
async def send_daily_message(context):
    user_ids = [6165060012]  # List of user IDs to send the message (could be dynamic based on active users)
    random_area_codes = random.sample(canadian_area_codes, 3)  # Select 3 random area codes

    message = f"আপনার দিনটি শুভ হোক 🌸\nআজকের কিছু Working Area কোড হচ্ছে: {', '.join(random_area_codes)}"
    
    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Error sending message to {user_id}: {e}")

# Schedule the daily message at 2 AM
def schedule_daily_message(app):
    scheduler = AsyncIOScheduler(timezone="Asia/Dhaka")
    scheduler.add_job(send_daily_message, 'cron', hour=2, minute=0, args=[app])
    scheduler.start()



# Twilio login
@permission_required
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("ржмрзНржпржмрж╣рж╛рж░: /login <SID> <AUTH_TOKEN>")
        return
    sid, token = context.args
    try:
        client = Client(sid, token)
        client.api.accounts(sid).fetch()
        user_clients[update.effective_user.id] = client
        await update.message.reply_text("тЬЕ рж▓ржЧржЗржи рж╕ржлрж▓!")
    except Exception as e:
        logging.exception("Login error:")
        await update.message.reply_text(f"рж▓ржЧржЗржи ржмрзНржпрж░рзНрже: {e}")

# Buy number
@permission_required
async def buy_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    client = user_clients.get(user_id)

    if not client:
        await update.message.reply_text("тЪая╕П ржЖржЧрзЗ /login ржХрж░рзБржиред")
        return

    try:
        if context.args:
            # ржЗржЙржЬрж╛рж░ ржпржжрж┐ Area Code ржжрзЗрзЯ
            area_code = context.args[0]
            numbers = client.available_phone_numbers("CA").local.list(area_code=area_code, limit=10)
        else:
            # ржЗржЙржЬрж╛рж░ ржпржжрж┐ ржХрж┐ржЫрзБ ржирж╛ ржжрзЗрзЯ, рждрж╛рж╣рж▓рзЗ рж░тАНрзНржпрж╛ржирзНржбржо ржХрж┐ржЫрзБ CA ржирж╛ржорзНржмрж╛рж░
            numbers = client.available_phone_numbers("CA").local.list(limit=10)

        if not numbers:
            await update.message.reply_text("ржирж╛ржорзНржмрж╛рж░ ржкрж╛ржУрзЯрж╛ ржпрж╛рзЯржирж┐ред")
            return

        user_available_numbers[user_id] = [n.phone_number for n in numbers]
        keyboard = [[InlineKeyboardButton(n.phone_number, callback_data=f"BUY:{n.phone_number}")] for n in numbers]
        keyboard.append([InlineKeyboardButton("Cancel тЭМ", callback_data="CANCEL")])

        await update.message.reply_text(
            "ржирж┐ржЪрзЗрж░ ржирж╛ржорзНржмрж╛рж░ржЧрзБрж▓рзЛ ржкрж╛ржУрзЯрж╛ ржЧрзЗржЫрзЗ:\n\n" + "\n".join(user_available_numbers[user_id]),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logging.exception("Buy number error:")
        await update.message.reply_text(f"рж╕ржорж╕рзНржпрж╛: {e}")

# Show messages
@permission_required
async def show_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = user_clients.get(update.effective_user.id)
    if not client:
        await update.message.reply_text("тЪая╕П ржЖржЧрзЗ /login ржХрж░рзБржиред")
        return
    try:
        msgs = client.messages.list(limit=20)
        incoming = [msg for msg in msgs if msg.direction == "inbound"]
        if not incoming:
            await update.message.reply_text("ржХрзЛржирзЛ Incoming Message ржкрж╛ржУрзЯрж╛ ржпрж╛рзЯржирж┐ред")
            return
        output = "\n\n".join([f"From: {m.from_}\nTo: {m.to}\nBody: {m.body}" for m in incoming[:5]])
        await update.message.reply_text(output)
    except Exception as e:
        logging.exception("Show messages error:")
        await update.message.reply_text(f"рж╕ржорж╕рзНржпрж╛: {e}")

# Delete number
@permission_required
async def delete_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = user_clients.get(update.effective_user.id)
    if not client:
        await update.message.reply_text("тЪая╕П ржЖржЧрзЗ /login ржХрж░рзБржиред")
        return
    try:
        numbers = client.incoming_phone_numbers.list(limit=1)
        if not numbers:
            await update.message.reply_text("ржирж╛ржорзНржмрж╛рж░ ржЦрзБржБржЬрзЗ ржкрж╛ржУрзЯрж╛ ржпрж╛рзЯржирж┐ред")
            return
        numbers[0].delete()
        await update.message.reply_text("тЬЕ ржирж╛ржорзНржмрж╛рж░ ржбрж┐рж▓рж┐ржЯ рж╣рзЯрзЗржЫрзЗред")
    except Exception as e:
        logging.exception("Delete number error:")
        await update.message.reply_text(f"ржбрж┐рж▓рж┐ржЯ ржХрж░рждрзЗ рж╕ржорж╕рзНржпрж╛: {e}")

# My numbers
@permission_required
async def my_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = user_clients.get(update.effective_user.id)
    if not client:
        await update.message.reply_text("тЪая╕П ржЖржЧрзЗ /login ржХрж░рзБржиред")
        return
    try:
        numbers = client.incoming_phone_numbers.list()
        if not numbers:
            await update.message.reply_text("ржЖржкржирж╛рж░ ржХрзЛржирзЛ ржирж╛ржорзНржмрж╛рж░ ржирзЗржЗред")
            return
        keyboard = [[InlineKeyboardButton(n.phone_number, callback_data=f"DELETE:{n.phone_number}")] for n in numbers]
        await update.message.reply_text("ржЖржкржирж╛рж░ ржирж╛ржорзНржмрж╛рж░ржЧрзБрж▓рзЛ:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logging.exception("My numbers error:")
        await update.message.reply_text(f"рж╕ржорж╕рзНржпрж╛: {e}")

# Admin Management
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("тЭМ ржЖржкржирж┐ ржПржЗ ржХржорж╛ржирзНржб ржмрзНржпржмрж╣рж╛рж░ ржХрж░рждрзЗ ржкрж╛рж░ржмрзЗржи ржирж╛ред")
        return
    try:
        new_admin = int(context.args[0])
        if new_admin not in ADMIN_IDS:
            ADMIN_IDS.append(new_admin)
            user_permissions[new_admin] = float("inf")
            await update.message.reply_text(f"тЬЕ {new_admin} ржПржЦржи Admin!")
        else:
            await update.message.reply_text("ржЗржЙржЬрж╛рж░ ржЗрждрж┐ржоржзрзНржпрзЗржЗ Adminред")
    except:
        await update.message.reply_text("тЭМ рж╕ржарж┐ржХржнрж╛ржмрзЗ user_id ржжрж┐ржиред")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS or len(ADMIN_IDS) <= 1:
        await update.message.reply_text("тЭМ ржПржЗ ржХржорж╛ржирзНржб ржЖржкржирж╛рж░ ржЬржирзНржп ржирж╛ред")
        return
    try:
        target_id = int(context.args[0])
        if target_id in ADMIN_IDS and target_id != user_id:
            ADMIN_IDS.remove(target_id)
            user_permissions.pop(target_id, None)
            await update.message.reply_text(f"тЬЕ {target_id} ржХрзЗ Admin ржерзЗржХрзЗ рж╕рж░рж╛ржирзЛ рж╣рзЯрзЗржЫрзЗред")
        else:
            await update.message.reply_text("тЭМ ржнрзБрж▓ ржЖржЗржбрж┐ред")
    except:
        await update.message.reply_text("тЭМ рж╕ржарж┐ржХржнрж╛ржмрзЗ user_id ржжрж┐ржиред")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("тЭМ ржЖржкржирж┐ ржПржЗ ржХржорж╛ржирзНржб ржмрзНржпржмрж╣рж╛рж░ ржХрж░рждрзЗ ржкрж╛рж░ржмрзЗржи ржирж╛ред")
        return
    msg = "ЁЯЫбя╕П Admin List:\n\n"
    for aid in ADMIN_IDS:
        try:
            user = await context.bot.get_chat(aid)
            msg += f"{user.full_name} тАФ @{user.username or 'N/A'} (ID: {aid})\n"
        except:
            msg += f"Unknown (ID: {aid})\n"
    await update.message.reply_text(msg)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("тЭМ ржЖржкржирж┐ ржПржЗ ржХржорж╛ржирзНржб ржмрзНржпржмрж╣рж╛рж░ ржХрж░рждрзЗ ржкрж╛рж░ржмрзЗржи ржирж╛ред")
        return
    msg = " ".join(context.args)
    success = fail = 0
    for uid in user_permissions:
        try:
            await context.bot.send_message(chat_id=uid, text=msg)
            success += 1
        except:
            fail += 1
    await update.message.reply_text(f"тЬЕ ржкрж╛ржарж╛ржирзЛ рж╣рзЯрзЗржЫрзЗ: {success}, тЭМ ржмрзНржпрж░рзНрже: {fail}")

# Button callback
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("BUY:"):
    number = data.split("BUY:")[1]
    client = user_clients.get(user_id)
    if not client:
        await query.edit_message_text("тЪая╕П ржЖржЧрзЗ /login ржХрж░рзБржиред")
        return
    try:
        existing = client.incoming_phone_numbers.list(limit=1)
        if existing:
            warn_msg = await query.edit_message_text("тЪая╕П ржжрзЯрж╛ ржХрж░рзЗ ржЖржкржирж╛рж░ ржЖржЧрзЗрж░ ржирж╛ржорзНржмрж╛рж░ ржЯрж┐ /delete_number ржХржорж╛ржирзНржб ржмрзНржпржмрж╣рж╛рж░ ржХрж░рзЗ ржбрж┐рж▓рзЗржЯ ржХрж░рзБржи")
            # 10 рж╕рзЗржХрзЗржирзНржб ржкрж░ ржбрж┐рж▓рж┐ржЯ ржХрж░рж╛ рж╣ржмрзЗ
            await asyncio.sleep(10)
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=warn_msg.message_id)
            except:
                pass  # ржпржжрж┐ ржПрж░ржоржзрзНржпрзЗ ржЗржЙржЬрж╛рж░ ржбрж┐рж▓рж┐ржЯ ржХрж░рзЗ ржлрзЗрж▓рзЗ
            return

        purchased = client.incoming_phone_numbers.create(phone_number=number)
        await query.edit_message_text(f"тЬЕ ржЖржкржирж┐ ржирж╛ржорзНржмрж╛рж░ржЯрж┐ ржХрж┐ржирзЗржЫрзЗржи: {purchased.phone_number}")
    except Exception as e:
        await query.edit_message_text(f"ржирж╛ржорзНржмрж╛рж░ ржХрзЗржирж╛ ржпрж╛рзЯржирж┐: {e}")


    elif data.startswith("DELETE:"):
        number = data.split("DELETE:")[1]
        client = user_clients.get(user_id)
        try:
            nums = client.incoming_phone_numbers.list(phone_number=number)
            if nums:
                nums[0].delete()
                await query.edit_message_text(f"тЬЕ ржирж╛ржорзНржмрж╛рж░ {number} ржбрж┐рж▓рж┐ржЯ рж╣рзЯрзЗржЫрзЗред")
            else:
                await query.edit_message_text("ржирж╛ржорзНржмрж╛рж░ ржкрж╛ржУрзЯрж╛ ржпрж╛рзЯржирж┐ред")
        except Exception as e:
            await query.edit_message_text(f"ржирж╛ржорзНржмрж╛рж░ ржбрж┐рж▓рж┐ржЯ ржХрж░рждрзЗ рж╕ржорж╕рзНржпрж╛: {e}")

    elif data == "CANCEL":
        await query.edit_message_text("ржирж╛ржорзНржмрж╛рж░ ржирж┐рж░рзНржмрж╛ржЪржи ржмрж╛рждрж┐рж▓ ржХрж░рж╛ рж╣рзЯрзЗржЫрзЗред")

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
                await query.edit_message_text("ржЖржкржирж┐ ржЗрждрж┐ржоржзрзНржпрзЗржЗ ржлрзНрж░рж┐ ржкрзНрж▓рж╛ржи ржмрзНржпржмрж╣рж╛рж░ ржХрж░рзЗржЫрзЗржиред")
                return
            user_used_free_plan.add(user_id)
            user_permissions[user_id] = time.time() + 3600
            await query.edit_message_text("тЬЕ ржЖржкржирж┐ рзз ржШржирзНржЯрж╛рж░ ржЬржирзНржп ржлрзНрж░рж┐ ржкрзНрж▓рж╛ржи ржПржХржЯрж┐ржн ржХрж░рзЗржЫрзЗржиред")
            return
        if plan in prices:
            _, label, cost = prices[plan]
            msg = (
                f"Please send {cost} to Binance Pay ID: 469628989\n"
                f"ржкрзЗржорзЗржирзНржЯ ржХрж░рж╛рж░ ржкрж░ ржкрзНрж░рзБржн ржкрж╛ржарж╛ржи Admin ржХрзЗ\n\n"
                f"User ID: {user_id}\nUsername: {username}\nPlan: {label} - {cost}"
            )
            await query.edit_message_text(msg)

# Start bot
def main():
    keep_alive()
    TOKEN = "7253583924:AAENVbdYNjHdbKHV0SJhnhoomyeOM2YeLXc"
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("grant", grant))
    app.add_handler(CommandHandler("active_users", active_users))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("buy_number", buy_number))
    app.add_handler(CommandHandler("show_messages", show_messages))
    app.add_handler(CommandHandler("delete_number", delete_number))
    app.add_handler(CommandHandler("my_numbers", my_numbers))
    app.add_handler(CommandHandler("add_admin", add_admin))
    app.add_handler(CommandHandler("remove_admin", remove_admin))
    app.add_handler(CommandHandler("list_admins", list_admins))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
