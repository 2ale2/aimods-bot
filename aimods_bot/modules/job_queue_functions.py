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
                                       parse_mode="MarkdownV2")
    except telegram.error.TelegramError as e:
        job_queue_logger.error(f'Not able to perform scheduled action: {e}')
