from telegram import Update

from aimods_bot.src.callbacks.panels.admin.tools.render import render_admin_tools_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation.admin import AdminTools
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def admin_tools_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_admin_tools_panel(update=update, context=context, base_path=root)
        case [AdminTools.CALENDAR]:
            pass

    return PCS.ADMIN_CONVERSATION
