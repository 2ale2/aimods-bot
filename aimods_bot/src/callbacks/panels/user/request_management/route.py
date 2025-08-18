from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.user.request_management.render import render_user_request_management_panel
from aimods_bot.src.callbacks.panels.user.request_management.request.route import user_request_route
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def requests_management_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_user_request_management_panel(update=update, context=context)
        return PCS.USER_CONVERSATION

    match path[0]:
        case "view_requests":
            pass
        case "add_request":
            return await user_request_route(update=update, context=context, path=path[1:])
