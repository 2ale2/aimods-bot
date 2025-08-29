from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin.moderation.route import moderation_router
from aimods_bot.src.callbacks.panels.admin.requests_management.route import admin_requests_management_route


async def admin_main_router(update: Update, context: CallbackContext):
    s = update.callback_query.data.split("/")

    # Expected "admin/<path>"
    if len(s) == 1:
        return await start(update=update, context=context)

    s.pop(0)
    try:
        match s[0]:
            case "moderation":
                return await moderation_router(update=update, context=context, path=s[1:])
            case "settings":
                pass
            case "manage_requests":
                return await admin_requests_management_route(update=update, context=context, path=s[1:])
            case "close":
                pass
    finally:
        await update.callback_query.answer()
