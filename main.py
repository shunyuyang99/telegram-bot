import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    user_id = update.effective_user.id
    users.add(user_id)

    text = (
        "🎉 Welcome to ACE88 Announcement Bot\n\n"
        "You will now receive:\n"
        "🔥 Free Credit Drops\n"
        "🔥 Limited Bonus Alerts\n"
        "🔥 VIP Promotions\n\n"
        "Stay tuned and good luck 🍀"
    )

    await update.message.reply_text(text)


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Total users: {len(users)}")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = " ".join(context.args)

    success = 0
    failed = 0

    for user in users:
        try:
            await context.bot.send_message(chat_id=user, text=message)
            success += 1
        except:
            failed += 1

    await update.message.reply_text(
        f"Broadcast completed.\n\nSuccess: {success}\nFailed: {failed}"
    )


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("users", users_command))
app.add_handler(CommandHandler("broadcast", broadcast))

print("Bot running...")

app.run_polling()
