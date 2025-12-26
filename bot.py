import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# ========= НАЛАШТУВАННЯ =========
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # в ENV на Railway
CHANNEL_ID = -1003534080985             # твій канал
KEYWORD = "2.2"
# ================================


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    # Текст може бути в caption (якщо це пост з картинкою)
    text = msg.text or msg.caption or ""
    if KEYWORD not in text:
        return

    # Якщо переслане повідомлення — форвардимо джерело,
    # інакше форвардимо те, що отримав бот.
    if msg.forward_from_chat and msg.forward_from_message_id:
        from_chat_id = msg.forward_from_chat.id
        message_id = msg.forward_from_message_id
    elif msg.forward_from_message_id and msg.forward_from_chat is None and msg.forward_from:
        # випадок форварду від юзера
        from_chat_id = msg.forward_from.id
        message_id = msg.forward_from_message_id
    else:
        from_chat_id = msg.chat_id
        message_id = msg.message_id

    await context.bot.forward_message(
        chat_id=CHANNEL_ID,
        from_chat_id=from_chat_id,
        message_id=message_id,
    )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Ловимо всі текстові / переслані / з підписом, без команд
    app.add_handler(MessageHandler(
        filters.TEXT | filters.CAPTION
        & ~filters.COMMAND,
        handle_message,
    ))

    app.run_polling()


if __name__ == "__main__":
    main()
