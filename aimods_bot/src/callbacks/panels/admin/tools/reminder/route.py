from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation.admin import ReminderRoute
from aimods_bot.src.helpers.models.routing import PathBuilder

from aimods_bot.src.callbacks.panels.admin.tools.reminder.render import render_admin_reminder_tool_panel


async def admin_reminder_tool_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_admin_reminder_tool_panel(
                update=update,
                context=context,
                base_path=root
            )
        case [ReminderRoute.RESUME_REMINDER_DRAFT]:
            pass
        case [ReminderRoute.ADD_REMINDER]:
            pass
        case [ReminderRoute.MANAGE_REMINDERS]:
            pass

    return PCS.ADMIN_CONVERSATION
