from telegram import Update

from aimods_bot.src.features.reminders.panels.route import admin_reminder_tool_route
from aimods_bot.src.callbacks.panels.admin.tools.render import render_admin_tools_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.ui.path_navigation.admin import AdminTools
from aimods_bot.src.ui.routing import PathBuilder
from aimods_bot.src.ui.conversation_states import PrivateConversationState as PCS


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
            return await admin_reminder_tool_route(
                update=update,
                context=context,
                root=root.add(AdminTools.REMINDER),
                relative_path=PathBuilder(*rest)
            )

    return PCS.ADMIN_CONVERSATION
