from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.route import moderation_router


async def admin_main_router(update: Update, context: CallbackContext):
    s = update.callback_query.data.split("/")
    try:
        match s[0]:
            case "moderation":
                return await moderation_router(update=update, context=context, path=s[1:])
            case "settings":
                pass
            case "requests":
                pass
            case "close":
                pass
    finally:
        await update.callback_query.answer()
