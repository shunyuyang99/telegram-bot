import os
from typing import Optional

import psycopg
from psycopg.rows import dict_row
from telegram import Update
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = str(os.getenv("ADMIN_ID", "")).strip()
DATABASE_URL = os.getenv("DATABASE_URL")

CONTENT_BONUS = "bonus"
CONTENT_RAIN = "rain"
CONTENT_TIPS = "tips"


def get_conn():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is missing")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    chat_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_content (
                    content_key TEXT PRIMARY KEY,
                    content_value TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                INSERT INTO bot_content (content_key, content_value)
                VALUES
                    (%s, %s),
                    (%s, %s),
                    (%s, %s)
                ON CONFLICT (content_key) DO NOTHING
            """, (
                CONTENT_BONUS, "No hot bonus set yet.",
                CONTENT_RAIN, "No Angpao Rain time set yet.",
                CONTENT_TIPS, "No game tips set yet."
            ))
        conn.commit()


def is_admin(chat_id: int) -> bool:
    return str(chat_id) == ADMIN_ID


def save_user(chat_id: int, username: str, first_name: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO subscribers (chat_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (chat_id)
                DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name
            """, (chat_id, username, first_name))
        conn.commit()


def remove_user(chat_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM subscribers WHERE chat_id = %s", (chat_id,))
        conn.commit()


def get_total_users() -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM subscribers")
            row = cur.fetchone()
            return int(row["total"])


def get_all_users() -> list[int]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT chat_id FROM subscribers ORDER BY joined_at ASC")
            rows = cur.fetchall()
            return [int(r["chat_id"]) for r in rows]


def set_content(key: str, value: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bot_content (content_key, content_value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (content_key)
                DO UPDATE SET
                    content_value = EXCLUDED.content_value,
                    updated_at = NOW()
            """, (key, value))
        conn.commit()


def get_content(key: str) -> str:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT content_value
                FROM bot_content
                WHERE content_key = %s
            """, (key,))
            row = cur.fetchone()
            return row["content_value"] if row else ""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    save_user(
        chat_id=chat_id,
        username=user.username or "",
        first_name=user.first_name or ""
    )

    await update.message.reply_text(
        "🎉 Welcome!\n\n"
        "You have successfully subscribed to this bot.\n"
        "Available commands:\n"
        "/bonus\n"
        "/rain\n"
        "/gametips"
    )


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("You are not allowed to use this command.")
        return

    total = get_total_users()
    await update.message.reply_text(f"Total subscribed users: {total}")


async def bonus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_content(CONTENT_BONUS))


async def rain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_content(CONTENT_RAIN))


async def gametips_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_content(CONTENT_TIPS))


async def setbonus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("You are not allowed to use this command.")
        return

    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Usage: /setbonus your hot bonus text")
        return

    set_content(CONTENT_BONUS, text)
    await update.message.reply_text("Bonus content updated.")


async def setrain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("You are not allowed to use this command.")
        return

    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Usage: /setrain Today Angpao Rain at 8:00 PM")
        return

    set_content(CONTENT_RAIN, text)
    await update.message.reply_text("Rain content updated.")


async def settips_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("You are not allowed to use this command.")
        return

    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Usage: /settips your game tips")
        return

    set_content(CONTENT_TIPS, text)
    await update.message.reply_text("Game tips updated.")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("You are not allowed to use this command.")
        return

    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Usage: /broadcast your message")
        return

    users = get_all_users()
    success = 0
    removed = 0
    failed = 0

    for chat_id in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            success += 1
        except Forbidden:
            remove_user(chat_id)
            removed += 1
        except BadRequest as e:
            msg = str(e).lower()
            if "chat not found" in msg or "user is deactivated" in msg:
                remove_user(chat_id)
                removed += 1
            else:
                failed += 1
        except TelegramError:
            failed += 1

    await update.message.reply_text(
        f"Broadcast completed.\n\n"
        f"Success: {success}\n"
        f"Removed: {removed}\n"
        f"Failed: {failed}"
    )


async def broadcastphoto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("You are not allowed to use this command.")
        return

    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text(
            "Usage:\n"
            "1. Reply to a photo\n"
            "2. Send /broadcastphoto optional caption"
        )
        return

    photo = update.message.reply_to_message.photo[-1]
    file_id = photo.file_id
    caption = " ".join(context.args).strip()

    users = get_all_users()
    success = 0
    removed = 0
    failed = 0

    for chat_id in users:
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=caption if caption else None
            )
            success += 1
        except Forbidden:
            remove_user(chat_id)
            removed += 1
        except BadRequest as e:
            msg = str(e).lower()
            if "chat not found" in msg or "user is deactivated" in msg:
                remove_user(chat_id)
                removed += 1
            else:
                failed += 1
        except TelegramError:
            failed += 1

    await update.message.reply_text(
        f"Photo broadcast completed.\n\n"
        f"Success: {success}\n"
        f"Removed: {removed}\n"
        f"Failed: {failed}"
    )


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN is missing")
    if not ADMIN_ID:
        raise ValueError("ADMIN_ID is missing")

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("broadcastphoto", broadcastphoto_command))

    app.add_handler(CommandHandler("bonus", bonus_command))
    app.add_handler(CommandHandler("rain", rain_command))
    app.add_handler(CommandHandler("gametips", gametips_command))

    app.add_handler(CommandHandler("setbonus", setbonus_command))
    app.add_handler(CommandHandler("setrain", setrain_command))
    app.add_handler(CommandHandler("settips", settips_command))

    print("Bot running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
