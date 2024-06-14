import telegram.error
from telegram.ext import ContextTypes

from loggers import job_queue_logger


async def scheduled_delete_message(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    if "chat_id" not in data or "message_id" not in data:
        job_queue_logger.warn("'chat_id' or 'message_id' are missing in JobQueue data.")
        return
    try:
        await context.bot.delete_message(chat_id=data["chat_id"], message_id=data["message_id"])
    except telegram.error.TelegramError as e:
        job_queue_logger.warn(f'Not able to perform scheduled action: {e}')


async def scheduled_send_message(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    if "chat_id" not in data or "text" not in data or "reply_markup" not in data:
        job_queue_logger.warn("'chat_id' or 'message_id' are missing in JobQueue data.")
        return
    try:
        await context.bot.send_message(chat_id=data["chat_id"], text=data["text"],
                                       reply_markup=data["reply_markup"],
                                       parse_mode="HTML")
    except telegram.error.TelegramError as e:
        job_queue_logger.error(f'Not able to perform scheduled action: {e}')


async def scheduled_edit_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data["chat_id"]
    message_id = context.job.data["message_id"]
    text = context.job.data["text"]

    reply_markup = context.job.data["reply_markup"] if "reply_markup" in context.job.data else None

    try:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                                            reply_markup=reply_markup, parse_mode="HTML")
    except telegram.error.TelegramError as e:
        job_queue_logger.error(f'Not able to perform scheduled action: {e}')
