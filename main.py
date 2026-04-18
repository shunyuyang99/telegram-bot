import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # 你的 Telegram 数字ID
DB_FILE = "subscribers.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_user(chat_id, username, first_name):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO subscribers (chat_id, username, first_name, joined_at)
        VALUES (?, ?, ?, ?)
    """, (
        chat_id,
        username,
        first_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()


def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM subscribers")
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_total_users():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscribers")
    total = cur.fetchone()[0]
    conn.close()
    return total


def remove_user(chat_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    save_user(chat_id, user.username or "", user.first_name or "")

    await update.message.reply_text(
        "🎉 Welcome!\n\n"
        "You have subscribed to our announcement bot."
    )


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(ADMIN_ID):
        await update.message.reply_text("You are not allowed to use this command.")
        return

    total = get_total_users()
    await update.message.reply_text(f"Total subscribed users: {total}")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(ADMIN_ID):
        await update.message.reply_text("You are not allowed to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast your message")
        return

    message = " ".join(context.args)
    users = get_all_users()

    success = 0
    failed = 0

    for chat_id in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            success += 1
        except Exception:
            failed += 1
            remove_user(chat_id)

    await update.message.reply_text(
        f"Broadcast completed.\n\nSuccess: {success}\nFailed/Removed: {failed}"
    )


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN is missing")

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("broadcast", broadcast))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
