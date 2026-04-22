import os
import psycopg
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id BIGINT PRIMARY KEY
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def add_user(chat_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (chat_id) VALUES (%s) ON CONFLICT (chat_id) DO NOTHING",
        (chat_id,)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM users")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row[0] for row in rows]

def get_user_count():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

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
    total = get_user_count()
    await update.message.reply_text(f"Total users: {total}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = " ".join(context.args)

    if not message:
        await update.message.reply_text("Usage: /broadcast your message here")
        return

    users = get_all_users()
    success = 0
    failed = 0

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"Broadcast completed.\n\nSuccess: {success}\nFailed: {failed}"
    )

def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("broadcast", broadcast))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
