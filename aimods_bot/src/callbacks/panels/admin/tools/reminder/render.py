from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext, ReminderWizard
from aimods_bot.src.helpers.constants.constants import ReminderField
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation.admin import ReminderRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.reminders_utils import list_reminders
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel

_TEXT_INPUT_STATE: dict[ReminderField, int] = {
    ReminderField.TITLE: PCS.SET_REMINDER_BODY,
    ReminderField.BODY: PCS.SET_REMINDER_BODY,
    ReminderField.ONCE_AT: PCS.SET_REMINDER_DATETIME,
    ReminderField.FIRE_TIME: PCS.SET_REMINDER_DATETIME,
}


def _get_header():
    return "<tg-emoji emoji-id=\"5411478619081953369\">📅</tg-emoji> <b>Menù Promemoria</b>\n\n"


async def render_admin_reminder_tool_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text, keyboard = await _get_admin_reminder_tool_panel_text_and_keyboard(context=context, base_path=base_path)
    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=keyboard
    )


async def _get_admin_reminder_tool_panel_text_and_keyboard(
        context: CustomContext,
        base_path: PathBuilder
) -> tuple[str, list[list[ButtonItem]]]:
    text = _get_header() + "🔹 Da qui puoi <b>gestire e creare i promemoria</b>."
    current_reminders = await list_reminders()
    if not current_reminders:
        text += "\n\nℹ️ Non ci sono promemoria."
    elif any(r.enabled for r in current_reminders):
        text += "\n\n💤 Non ci sono promemoria attivi."
    text += "\n\n🔸 Scegli un'opzione."

    keyboard = []
    if context.pydc.persistent.active_reminder_wizard:
        keyboard.append(
            [ButtonItem(text="✏️ Riprendi Bozza", callback_key=base_path.add(ReminderRoute.RESUME_REMINDER_DRAFT))]
        )

    keyboard.append([ButtonItem(text="➕ Nuovo Promemoria", callback_key=base_path.add(ReminderRoute.ADD_REMINDER))])
    if not current_reminders:
        keyboard[-1].append(
            ButtonItem(text="🗃️ Gestisci Promemoria", callback_key=base_path.add(ReminderRoute.MANAGE_REMINDERS))
        )

    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])

    return text, keyboard


async def render_reminder_wizard_step(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        wizard: ReminderWizard,
) -> int:
    """
    Disegna lo stato corrente del wizard: la domanda in sospeso o il riepilogo.

    Presuppone che `advance_or_finish_wizard()` sia già stato chiamato: legge
    `requesting`, non lo ricalcola.
    """
    if wizard.requesting is None:
        await render_reminder_summary_panel(
            update=update,
            context=context,
            base_path=base_path,
            wizard=wizard
        )
        return PCS.ADMIN_CONVERSATION

    field = wizard.requesting
    state = _TEXT_INPUT_STATE.get(field, PCS.ADMIN_CONVERSATION)

    if state != PCS.ADMIN_CONVERSATION:
        context.pydc.persistent.bot_message_id = update.effective_message.id
        context.pydc.persistent.root_path = base_path.build()

    await render_reminder_question_panel(
        update=update,
        context=context,
        base_path=base_path,
        wizard=wizard,
        field=field
    )
    return state
