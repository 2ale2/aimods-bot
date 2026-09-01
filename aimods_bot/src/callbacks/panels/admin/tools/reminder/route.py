from telegram import Update
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation.admin import ReminderRoute
from aimods_bot.src.helpers.models.routing import PathBuilder


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
                root=root,
                relative_path=relative_path
            )
        case [ReminderRoute.RESUME_REMINDER_DRAFT]:
            pass
        case [ReminderRoute.ADD_REMINDER]:
            pass
        case [ReminderRoute.MANAGE_REMINDERS]:
            pass
