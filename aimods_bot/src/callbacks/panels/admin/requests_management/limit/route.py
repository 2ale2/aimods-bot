from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import render_admin_limit_user_request_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def route_admin_limit_user_request(update: Update, context: ContextTypes.DEFAULT_TYPE, path: list[str]):
    if len(path) == 0:
        await render_admin_limit_user_request_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION
