from telegram import Update
from telegram.ext import InvalidCallbackData

from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState
from aimods_bot.src.helpers.constants.path_navigation import AdminRoute, GlobalAction

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin.moderation.route import moderation_router
from aimods_bot.src.callbacks.panels.admin.requests_management.route import admin_requests_management_route
from aimods_bot.src.callbacks.panels.admin.settings_management.route import admin_settings_management_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet, safe_delete


async def admin_main_router(update: Update, context: CustomContext):
    if not update.callback_query:
        raise ValueError("No callback query in Update!")

    c_data = update.callback_query.data
    if isinstance(c_data, InvalidCallbackData):
        return await start(update=update, context=context)

    if c_data is None:
        raise ValueError("Callback data must not be None!")

    path = PathBuilder.from_string(c_data)

    # Expected "admin/<path>"
    if path.segments and path.segments[0] == AdminRoute.ROOT:
        path = path.pop(0)

    if not len(path):
        return await start(update=update, context=context)

    try:
        match path.segments:
            case [AdminRoute.MODERATION]:
                await not_implemented_yet(update=update, context=context)
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
            case [close_action] if close_action in (GlobalAction.CLOSE_MENU, GlobalAction.CLOSE):
                await safe_delete(update=update, context=context)

        return PrivateConversationState.ADMIN_CONVERSATION
    finally:
        await update.callback_query.answer()
