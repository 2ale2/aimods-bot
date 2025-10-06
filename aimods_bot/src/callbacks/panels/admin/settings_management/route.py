from telegram import Update

from aimods_bot.src.callbacks.panels.admin.settings_management.render import render_admin_settings_management_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def admin_settings_management_route(update: Update, context: CustomContext, path: list[str]):
    if len(path) == 0:
        await render_admin_settings_management_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "notifications":
            pass
