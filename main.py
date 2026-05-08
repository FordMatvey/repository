import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==== НАСТРОЙКИ ====
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))

# Связь: id сообщения в группе → id пользователя
message_map: dict[int, int] = {}

# Логирование (чтобы видеть, что бот жив)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ==== ХЕНДЛЕРЫ ====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветствие по /start в личке."""
    if update.message is None:
        return

    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Я бот проекта по сборке кастомных ПК.\n"
        "Наш слоган: *Компьютер, который вы не забудете*.\n\n"
        "Напиши своё сообщение — я передам его менеджеру.",
        parse_mode="Markdown",
    )


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Любое текстовое сообщение от пользователя в ЛС → в группу."""
    if update.message is None:
        return

    user = update.message.from_user
    text = update.message.text or ""

    logger.info("Сообщение от пользователя %s (%s): %s", user.id, user.username, text)

    # Отправляем сообщение в группу
    sent = await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=f"💬 Сообщение от @{user.username or user.id}:\n\n{text}",
    )

    # Запоминаем связь: id сообщения в группе → id чата пользователя
    message_map[sent.message_id] = update.message.chat_id
    logger.info("Связал group_msg_id=%s с user_chat_id=%s", sent.message_id, update.message.chat_id)


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ответ в группе (reply на сообщение бота) → обратно пользователю."""
    if update.message is None:
        return

    msg = update.message

    # Нас интересуют только ответы (reply) на сообщения бота
    if msg.reply_to_message is None:
        return

    original_group_msg_id = msg.reply_to_message.message_id
    logger.info("Пришёл reply в группе на msg_id=%s", original_group_msg_id)

    if original_group_msg_id not in message_map:
        logger.info("Этого msg_id нет в message_map, игнорирую")
        return

    user_chat_id = message_map[original_group_msg_id]
    text = msg.text or ""

    logger.info("Отправляю ответ менеджера пользователю chat_id=%s: %s", user_chat_id, text)

    await context.bot.send_message(
        chat_id=user_chat_id,
        text=f"Ответ менеджера:\n\n{text}",
    )


def main() -> None:
    # Создаём приложение
    app = Application.builder().token(BOT_TOKEN).build()

    # /start в личке
    app.add_handler(CommandHandler("start", start))

    # Любой текст в ЛС → в группу
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            handle_user_message,
        )
    )

    # Любой текст в конкретной группе → проверяем, не reply ли это
    app.add_handler(
        MessageHandler(
            filters.Chat(GROUP_CHAT_ID) & filters.TEXT & ~filters.COMMAND,
            handle_group_message,
        )
    )

    logger.info("Бот запущен, жду апдейты...")
    app.run_polling()


if __name__ == "__main__":
    main()
