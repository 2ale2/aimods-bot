from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation.admin import ReminderRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.reminders_utils import list_reminders
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel


def _get_header():
    return "<tg-emoji emoji-id=\"5411478619081953369\">📅</tg-emoji> <b>Menù Promemoria</b>\n\n"


async def render_admin_reminder_tool_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text, keyboard = await _get_admin_reminder_tool_panel_text(context=context, base_path=base_path)
    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=keyboard
    )


async def _get_admin_reminder_tool_panel_text_and_keyboard(context: CustomContext, base_path: PathBuilder) -> tuple[str, list[list[ButtonItem]]]:
    text = _get_header() + "\n\n🔹 Da qui puoi <b>gestire e creare i promemoria</b>."
    no_reminders = not await list_reminders()
    if no_reminders:
        text += "\n\nℹ️ Non ci sono promemoria."
    elif not await list_reminders(only_enabled=True):
        text += "\n\n💤 Non ci sono promemoria attivi."
    text += "\n\n🔸 Scegli un'opzione."

    keyboard = []
    if context.pydc.persistent.active_reminder_wizard:
        keyboard.append(
            [ButtonItem(text="✏️ Riprendi Bozza", callback_key=base_path.add(ReminderRoute.RESUME_REMINDER_DRAFT))]
        )

    keyboard.append([ButtonItem(text="➕ Nuovo Promemoria", callback_key=base_path.add(ReminderRoute.ADD_REMINDER))])
    if not no_reminders:
        keyboard[-1].append(
            ButtonItem(text="🗃️ Gestisci Promemoria", callback_key=base_path.add(ReminderRoute.MANAGE_REMINDERS))
        )

    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])

    return text, keyboard
