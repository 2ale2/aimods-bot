from telegram import Update
from telegram.ext import CallbackContext


async def admin_main_router(update: Update, context: CallbackContext):
    s = update.callback_query.data.split("/", 1)
    match s[0]:
        case "moderation":
            pass
        case "settings":
            pass
        case "requests":
            pass
        case "close":
            pass
