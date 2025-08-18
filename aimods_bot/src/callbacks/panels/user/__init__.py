from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.user.request_management.route import requests_management_route
from aimods_bot.src.callbacks.commands.general.start_command import start


async def user_main_router(update: Update, context: CallbackContext):
    c_data = update.callback_query.data
    path = c_data.split("/")

    if len(path) == 1:
        return await start(update=update, context=context)

    path.pop(0)
    try:
        match path[0]:
            case "manage_requests":
                return await requests_management_route(update=update, context=context, path=path[1:])
    finally:
        await update.callback_query.answer()
