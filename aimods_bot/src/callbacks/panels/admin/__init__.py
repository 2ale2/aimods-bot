from telegram import Update
from telegram.ext import InvalidCallbackData

from aimods_bot.src.helpers.constants.conversation_paths.navigation import AdminRoute, GlobalAction

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin.moderation.route import moderation_router
from aimods_bot.src.callbacks.panels.admin.requests_management.route import admin_requests_management_route
from aimods_bot.src.callbacks.panels.admin.settings_management.route import admin_settings_management_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def admin_main_router(update: Update, context: CustomContext):
    c_data = update.callback_query.data
    if isinstance(c_data, InvalidCallbackData):
        return await start(update=update, context=context)

    path = PathBuilder.from_string(c_data)

    # Expected "admin/<path>"
    if len(path) == 1:
        return await start(update=update, context=context)

    path = path.pop(0)

    try:
        match path.segments:
            case [AdminRoute.MODERATION, *sub_path]:
                return await not_implemented_yet(update=update, context=context)
                # return await moderation_router(update=update, context=context, path=s[1:])
            case [AdminRoute.SETTINGS, *sub_path]:
                return await admin_settings_management_route(
                    update=update,
                    context=context,
                    root=PathBuilder(AdminRoute.SETTINGS),
                    relative_path=PathBuilder(*sub_path)
                )
            case [AdminRoute.REQUESTS, *sub_path]:
                return await admin_requests_management_route(
                    update=update,
                    context=context,
                    root=PathBuilder(AdminRoute.REQUESTS),
                    relative_path=PathBuilder(*sub_path)
                )
            case GlobalAction.CLOSE:
                pass

    finally:
        await update.callback_query.answer()
