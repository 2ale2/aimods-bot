from telegram import Update

from aimods_bot.src.callbacks.panels.admin.tools.reminder.route import admin_reminder_tool_route
from aimods_bot.src.callbacks.panels.admin.tools.render import render_admin_tools_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation.admin import AdminTools
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def admin_tools_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_admin_tools_panel(update=update, context=context, base_path=root)
        case [AdminTools.REMINDER, *rest]:
            await admin_reminder_tool_route(
                update=update,
                context=context,
                root=root.add(AdminTools.REMINDER),
                relative_path=PathBuilder(*rest)
            )

    return PCS.ADMIN_CONVERSATION
