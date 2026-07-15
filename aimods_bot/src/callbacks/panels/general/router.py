from telegram import Update
from telegram.ext import InvalidCallbackData, ConversationHandler

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin import admin_main_router
from aimods_bot.src.callbacks.panels.user import user_main_router
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation import UserRoute, AdminRoute
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder

log = logger.getChild(__name__)


async def general_router(update: Update, context: CustomContext):
    if not update.callback_query:
        raise ValueError("No callback query in Update!")

    c_data = update.callback_query.data
    if isinstance(c_data, InvalidCallbackData):
        return await start(update=update, context=context)

    if c_data is None:
        raise ValueError("Callback data must not be None!")

    path = PathBuilder.from_string(c_data)
    match path.segments[0]:
        case UserRoute.ROOT:
            return await user_main_router(update=update, context=context)
        case AdminRoute.ROOT:
            return await admin_main_router(update=update, context=context)
        case _:
            log.warning(f"Unhandled path in {__name__}: {c_data}")
            return ConversationHandler.END
