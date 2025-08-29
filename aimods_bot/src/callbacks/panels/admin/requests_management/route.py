from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.callbacks.panels.admin.requests_management.render import render_admin_request_management_panel, \
    render_admin_active_requests_management_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def admin_requests_management_route(update: Update, context: ContextTypes.DEFAULT_TYPE, path: list[str]):
    if len(path) == 0:
        await render_admin_request_management_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "active_requests":
            pass
        case "manage_topics":
            pass
        case "limit_user_request":
            pass

    return PCS.ADMIN_CONVERSATION


async def admin_active_requests_management_route(update: Update, context: ContextTypes.DEFAULT_TYPE, path: list[str]):
    if len(path) == 0:
        await render_admin_active_requests_management_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:


