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
    if not update.callback_query:
        raise ValueError("No callback query in Update!")

    c_data = update.callback_query.data
    if isinstance(c_data, InvalidCallbackData):
        return await start(update=update, context=context)

    path = PathBuilder.from_string(c_data)

    # Expected "admin/<path>"
    if len(path) == 1:
        return await start(update=update, context=context)

    path.pop(0)

    try:
        match path.segments:
            case [AdminRoute.MODERATION, *sub_path]:
                return await not_implemented_yet(update=update, context=context)
                # return await moderation_router(update=update, context=context, path=s[1:])
            case [AdminRoute.MANAGE_SETTINGS, *sub_path]:
                return await admin_settings_management_route(
                    update=update,
                    context=context,
                    root=PathBuilder(AdminRoute.MANAGE_SETTINGS),
                    relative_path=PathBuilder(*sub_path)
                )
            case [AdminRoute.MANAGE_REQUESTS, *sub_path]:
                return await admin_requests_management_route(
                    update=update,
                    context=context,
                    root=PathBuilder(AdminRoute.MANAGE_REQUESTS),
                    relative_path=PathBuilder(*sub_path)
                )
            case GlobalAction.CLOSE_MENU:
                pass

    finally:
        await update.callback_query.answer()
