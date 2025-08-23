from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.callbacks.panels.user.request.management.render import render_user_request_management_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def user_request_management_route(update: Update, context: ContextTypes.DEFAULT_TYPE, path: list[str]):
    if len(path) == 0:
        await render_user_request_management_panel(update=update, context=context)
        return PCS.USER_CONVERSATION

    match path[0]:
        case "android":
            pass
        case "windows":
            pass
        case "ios":
            pass
        case "macos":
            pass
