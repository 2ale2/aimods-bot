import html

from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext, ReminderWizard
from aimods_bot.src.helpers.constants.constants import ReminderField, Recurrence, WEEKDAYS, REMINDER_TIME_FORMAT, \
    REMINDER_DATETIME_FORMAT
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction
from aimods_bot.src.helpers.constants.path_navigation.admin import ReminderRoute
from aimods_bot.src.helpers.models.reminders import LAST_DAY_OF_MONTH
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

_INTERVAL_PRESETS = (2, 3, 5, 7, 10, 14, 30)
_BODY_PREVIEW_LIMIT = 200


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
    elif not any(r.enabled for r in current_reminders):
        text += "\n\n💤 Non ci sono promemoria attivi."
    text += "\n\n🔸 Scegli un'opzione."

    keyboard = []
    if context.pydc.persistent.active_reminder_wizard:
        keyboard.append(
            [ButtonItem(text="✏️ Riprendi Bozza", callback_key=base_path.add(ReminderRoute.DRAFT))]
        )

    keyboard.append([ButtonItem(text="➕ Nuovo Promemoria", callback_key=base_path.add(ReminderRoute.ADD_REMINDER))])
    if current_reminders:
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
        message_id: int | None = None
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
            wizard=wizard,
            message_id=message_id
        )
        return PCS.ADMIN_CONVERSATION

    field = wizard.requesting
    state = _TEXT_INPUT_STATE.get(field, PCS.ADMIN_CONVERSATION)

    if state != PCS.ADMIN_CONVERSATION and update.callback_query:
        context.pydc.persistent.bot_message_id = update.effective_message.id
        context.pydc.persistent.root_path = base_path.build()

    await render_reminder_question_panel(
        update=update,
        context=context,
        base_path=base_path,
        wizard=wizard,
        field=field,
        message_id=message_id
    )
    return state


def _format_field_value(wizard: ReminderWizard, field: ReminderField) -> str:
    """Rende leggibile il valore di un campo. Titolo e corpo sono escapati: i pannelli sono in HTML."""
    value = getattr(wizard, field.value)
    if value is None:
        return "<i>da compilare</i>"

    match field:
        case ReminderField.TITLE:
            return html.escape(value)
        case ReminderField.BODY:
            preview = value if len(value) <= _BODY_PREVIEW_LIMIT else value[:_BODY_PREVIEW_LIMIT].rstrip() + "…"
            return html.escape(preview)
        case ReminderField.RECURRENCE:
            if not isinstance(value, Recurrence):
                raise ValueError(f"Field {field} type must be a Recurrence instance, got {type(value)}")
            return value.label
        case ReminderField.INTERVAL_DAYS:
            return "ogni giorno" if value == 1 else f"ogni {value} giorni"
        case ReminderField.DAY_OF_WEEK:
            return WEEKDAYS[value]
        case ReminderField.DAY_OF_MONTH:
            return "ultimo giorno del mese" if value == LAST_DAY_OF_MONTH else f"giorno {value}"
        case ReminderField.FIRE_TIME:
            return value.strftime(REMINDER_TIME_FORMAT)
        case ReminderField.ONCE_AT:
            return value.strftime(REMINDER_DATETIME_FORMAT)


def _format_draft(wizard: ReminderWizard) -> str:
    """Righe del riepilogo. Cicla su `flow`, non su tutti i campi."""
    return "\n".join(
        f"🔹 <b>{field.label}</b> — {_format_field_value(wizard=wizard, field=field)}"
        for field in wizard.flow
    )


def _value_keyboard(field: ReminderField, field_path: PathBuilder) -> list[list[ButtonItem]]:
    """Bottoni di risposta per i campi a valore chiuso. Lista vuota per i campi testuali."""
    match field:
        case ReminderField.RECURRENCE:
            return [
                [
                    ButtonItem(text="1️⃣ Una Volta", callback_key=field_path.add(Recurrence.ONCE)),
                    ButtonItem(text="☀️ Giornaliero", callback_key=field_path.add(ReminderRoute.DAILY)),
                ],
                [
                    ButtonItem(text="🔢 A Intervalli", callback_key=field_path.add(Recurrence.INTERVAL)),
                ],
                [
                    ButtonItem(text="📅 Settimanale", callback_key=field_path.add(Recurrence.WEEKLY)),
                    ButtonItem(text="🗓 Mensile", callback_key=field_path.add(Recurrence.MONTHLY)),
                ],
            ]

        case ReminderField.INTERVAL_DAYS:
            buttons = [
                ButtonItem(text=f"{days}", callback_key=field_path.add(str(days)))
                for days in _INTERVAL_PRESETS
            ]
            return [buttons[i:i + 4] for i in range(0, len(buttons), 4)]

        case ReminderField.DAY_OF_WEEK:
            buttons = [
                ButtonItem(text=name[:3], callback_key=field_path.add(str(index)))
                for index, name in enumerate(WEEKDAYS)
            ]
            return [buttons[:4], buttons[4:]]

        case ReminderField.DAY_OF_MONTH:
            buttons = [
                ButtonItem(text=f"{day}", callback_key=field_path.add(str(day)))
                for day in range(1, 32)
            ]
            rows = [buttons[i:i + 7] for i in range(0, len(buttons), 7)]
            rows.append([
                ButtonItem(text="🏁 Ultimo Giorno", callback_key=field_path.add(str(LAST_DAY_OF_MONTH)))
            ])
            return rows

        case _:
            return []


async def render_reminder_summary_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        wizard: ReminderWizard,
        message_id: int | None = None
):
    """Riepilogo della bozza. Idempotente: si può ridisegnare quante volte si vuole."""
    text = _get_header()
    text += "🔹 <b>Riepilogo del promemoria</b>\n\n"
    text += _format_draft(wizard=wizard)
    text += "\n\n🔸 Tocca un campo per <b>modificarlo</b>, oppure conferma."

    field_buttons = [
        ButtonItem(text=f"✏️ {field.label}", callback_key=base_path.add(field))
        for field in wizard.flow
    ]
    keyboard = [field_buttons[i:i + 2] for i in range(0, len(field_buttons), 2)]

    if wizard.is_complete:
        keyboard.append([
            ButtonItem(text="✅ Conferma", callback_key=base_path.add(GlobalAction.CONFIRM))
        ])

    keyboard.append([
        ButtonItem(text="🗑 Annulla Bozza", callback_key=base_path.add(ReminderRoute.CANCEL_DRAFT)),
        ButtonItem(text="🔙 Menù", callback_key=base_path.back()),
    ])

    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=keyboard,
        message_id=message_id
    )


async def render_reminder_question_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        wizard: ReminderWizard,
        field: ReminderField,
        message_id: int | None = None
):
    """Domanda singola. In modifica mostra il valore attuale e la via di fuga verso il riepilogo."""
    text = _get_header()

    if wizard.editing:
        text += (f"✏️ <b>Modifica — {field.label}</b>\n\n"
                 f"🔹 Valore attuale: {_format_field_value(wizard=wizard, field=field)}\n\n")
    else:
        step = wizard.flow.index(field) + 1
        text += f"🔹 <b>{field.label}</b> — <i>passo {step} di {len(wizard.flow)}</i>\n\n"

    text += field.wizard_question()

    keyboard = _value_keyboard(field=field, field_path=base_path.add(field))

    if wizard.editing:
        keyboard.append([
            ButtonItem(text="↩️ Annulla Modifica", callback_key=base_path.add(ReminderRoute.BACK_TO_SUMMARY))
        ])

    keyboard.append([
        ButtonItem(text="🗑 Annulla Bozza", callback_key=base_path.add(ReminderRoute.CANCEL_DRAFT)),
        ButtonItem(text="🔙 Menù", callback_key=base_path.back()),
    ])

    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=keyboard,
        message_id=message_id
    )
