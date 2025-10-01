from telegram import Update
from telegram.ext import InvalidCallbackData

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin.moderation.route import moderation_router
from aimods_bot.src.callbacks.panels.admin.requests_management.route import admin_requests_management_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def admin_main_router(update: Update, context: CustomContext):
    c_data = update.callback_query.data
    if isinstance(c_data, InvalidCallbackData):
        return await start(update=update, context=context)

    s = c_data.split("/")

    # Expected "admin/<path>"
    if len(s) == 1:
        return await start(update=update, context=context)

    s.pop(0)
    try:
        match s[0]:
            case "moderation":
                return await not_implemented_yet(update=update, context=context)
                # return await moderation_router(update=update, context=context, path=s[1:])
            case "settings":
                return await not_implemented_yet(update=update, context=context)
            case "manage_requests":
                return await admin_requests_management_route(update=update, context=context, path=s[1:])
            case "close":
                pass
    finally:
        await update.callback_query.answer()
