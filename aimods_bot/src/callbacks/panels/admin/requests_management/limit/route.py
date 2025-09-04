from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import render_admin_limit_user_request_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def route_admin_limit_user_request(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        path: list[str],
        user_id: int
):
    if len(path) == 0:
        await render_admin_limit_user_request_panel(update=update, context=context, user_id=user_id)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "duration":

