from telegram import Update
from telegram.ext import InvalidCallbackData

from aimods_bot.src.callbacks.panels.user.request.route import requests_management_route
from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.core.customcontext import CustomContext


async def user_main_router(update: Update, context: CustomContext):
    c_data = update.callback_query.data

    if isinstance(c_data, InvalidCallbackData):
        return await start(update=update, context=context)

    path = c_data.split("/")

    if len(path) == 1:
        return await start(update=update, context=context)

    path.pop(0)
    try:
        if path[0] in ("add_request", "view_requests"):
            return await requests_management_route(update=update, context=context, path=path)
    finally:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
