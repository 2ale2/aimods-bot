from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete


async def reset_user_data(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context)
    if update.effective_chat.type != "private":
        return

    if not len(context.args) or not context.args[0].isdigit():
        await update.effective_message.reply_text(text="⚠ Indica uno user ID", allow_sending_without_reply=True)
        return

    user_id = int(context.args[0])

    context.application.drop_user_data(user_id=user_id)
    context.application.drop_chat_data(chat_id=user_id)

    await update.effective_message.reply_text(text="✔ Utente Resettato", allow_sending_without_reply=True)
