from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.utils.telegram_utils import safe_delete


async def check_status(update: Update, context: ContextTypes. DEFAULT_TYPE):
    await safe_delete(update, context)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Status OK"
    )
