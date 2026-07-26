from telegram import Update
from telegram.ext import InvalidCallbackData, ConversationHandler

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.user.request.route import user_requests_management_route
from aimods_bot.src.callbacks.panels.user.settings_management.route import user_settings_management_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState
from aimods_bot.src.helpers.constants.path_navigation import UserRoute, GlobalAction
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.utils.user_utils import check_auth

log = logger.getChild(__name__)


@check_auth()
async def user_main_router(update: Update, context: CustomContext):
    if not update.callback_query:
        raise ValueError("No callback query in Update!")

    c_data = update.callback_query.data
    if isinstance(c_data, InvalidCallbackData):
        return await start(update=update, context=context)

    if c_data is None:
        raise ValueError("Callback data must not be None!")

    path = PathBuilder.from_string(c_data)

    # Expected "admin/<path>"
    if path.segments and path.segments[0] == UserRoute.ROOT:
        path = path.pop(0)

    if not len(path):
        return await start(update=update, context=context)

    try:
        match path.segments:
            case [main_route_el, *rest] if main_route_el in (UserRoute.ADD_REQUEST, UserRoute.VIEW_REQUESTS):
                return await user_requests_management_route(
                    update=update,
                    context=context,
                    root=PathBuilder(main_route_el),
                    relative_path=PathBuilder(*rest)
                )
            case [UserRoute.MANAGE_SETTINGS, *rest]:
                return await user_settings_management_route(
                    update=update,
                    context=context,
                    root=PathBuilder(UserRoute.MANAGE_SETTINGS),
                    relative_path=PathBuilder(*rest)
                )

            case [close_action] if close_action in (GlobalAction.CLOSE_MENU, GlobalAction.CLOSE):
                await safe_delete(update=update, context=context)
                if close_action == GlobalAction.CLOSE_MENU:
                    return ConversationHandler.END
                return PrivateConversationState.USER_CONVERSATION
    finally:
        await update.callback_query.answer()
