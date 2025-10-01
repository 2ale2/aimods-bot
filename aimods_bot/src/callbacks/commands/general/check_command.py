from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete


async def check_status(update: Update, context: CustomContext):
    await safe_delete(update, context)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Status OK"
    )
