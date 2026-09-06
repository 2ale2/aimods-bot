from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode

from aimods_bot.src.callbacks.panels.admin.tools.reminder.render import render_reminder_wizard_step
from aimods_bot.src.core.customcontext import ReminderWizard, CustomContext
from aimods_bot.src.helpers.constants.constants import ReminderField, Recurrence
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction
from aimods_bot.src.helpers.constants.path_navigation.admin import ReminderRoute
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.reminders import LAST_DAY_OF_MONTH
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.utils.time_utils import parse_clock_time, parse_absolute_datetime, is_nonexistent_local_time

log = logger.getChild(__name__)


def handle_reminder_field_value(wizard: ReminderWizard, field: ReminderField, raw_value: str) -> bool:
    match field:
        case ReminderField.RECURRENCE:
            if raw_value == ReminderRoute.DAILY:
                wizard.set_recurrence(Recurrence.INTERVAL)
                wizard.interval_days = 1
                return True
            try:
                wizard.set_recurrence(Recurrence(raw_value))
            except ValueError:
                return False
            return True

        case ReminderField.INTERVAL_DAYS:
            days = _to_int(raw_value)
            if days is None or days < 1:
                return False
            wizard.interval_days = days
            return True

        case ReminderField.DAY_OF_WEEK:
            day = _to_int(raw_value)
            if day is None or not 0 <= day <= 6:  # 0 = lunedì
                return False
            wizard.day_of_week = day
            return True

        case ReminderField.DAY_OF_MONTH:
            day = _to_int(raw_value)
            if day is None or not (day == LAST_DAY_OF_MONTH or 1 <= day <= 31):
                return False
            wizard.day_of_month = day
            return True

        case _:
            log.warning(f"{field} does not accept callback input.")
            return False


async def _redraw(update: Update, context: CustomContext) -> int:
    """Ridisegna il passo corrente sul pannello salvato. Non azzera il path: i campi testuali sono consecutivi."""
    wizard = context.pydc.persistent.active_reminder_wizard
    return await render_reminder_wizard_step(
        update=update,
        context=context,
        base_path=PathBuilder.from_string(context.pydc.persistent.root_path),
        wizard=wizard,
        message_id=context.pydc.persistent.bot_message_id
    )


async def _reject(update: Update, context: CustomContext, reason: str, state: int) -> int:
    """Input non valido: avvisa e lascia il wizard esattamente com'era."""
    await update.effective_message.reply_text(
        text=reason,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(text="🚮 Chiudi", callback_data=GlobalAction.CLOSE_MENU)]
        ]),
        parse_mode=ParseMode.HTML
    )
    return state


async def handle_reminder_text_field(update: Update, context: CustomContext) -> int:
    """TITLE e BODY: un solo stato per due campi, distingue `wizard.requesting`."""
    wizard = context.pydc.persistent.active_reminder_wizard
    raw = (update.effective_message.text or "").strip()
    await safe_delete(update=update, context=context)

    if wizard is None or wizard.requesting not in (ReminderField.TITLE, ReminderField.BODY):
        log.warning("Text input received with no reminder field pending.")
        await safe_delete(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    field = wizard.requesting
    if not raw:
        return await _reject(update, context, "⚠️ Il testo non può essere vuoto.", PCS.SET_REMINDER_BODY)

    setattr(wizard, field.value, raw)
    move_cursor_after_answer(wizard=wizard, field=field)

    return await _redraw(update=update, context=context)


async def handle_reminder_datetime_field(update: Update, context: CustomContext) -> int:
    """ONCE_AT e FIRE_TIME: formati diversi, stesso stato."""
    wizard = context.pydc.persistent.active_reminder_wizard
    raw = (update.effective_message.text or "").strip()

    if wizard is None or wizard.requesting not in (ReminderField.ONCE_AT, ReminderField.FIRE_TIME):
        log.warning("Datetime input received with no reminder field pending.")
        await safe_delete(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    field = wizard.requesting

    if field is ReminderField.FIRE_TIME:
        parsed = parse_clock_time(raw)
        if parsed is None:
            return await _reject(
                update, context,
                "⚠️ Formato non valido. Usa <code>HH:MM</code>, ad esempio <code>09:00</code>.",
                PCS.SET_REMINDER_DATETIME
            )
    else:
        parsed = parse_absolute_datetime(raw)
        if parsed is None:
            return await _reject(
                update, context,
                "⚠️ Formato non valido. Usa <code>GG/MM/AAAA HH:MM</code>, "
                "ad esempio <code>05/03/2026 14:30</code>.",
                PCS.SET_REMINDER_DATETIME
            )
        if parsed <= datetime.now():
            return await _reject(
                update, context,
                "⚠️ La data indicata è già passata.",
                PCS.SET_REMINDER_DATETIME
            )
        if is_nonexistent_local_time(parsed):
            return await _reject(
                update, context,
                "⚠️ Quell'orario non esiste: è la notte del cambio d'ora, "
                "in cui le lancette saltano da <b>02:00</b> a <b>03:00</b>. Scegline un altro.",
                PCS.SET_REMINDER_DATETIME
            )

    await safe_delete(update=update, context=context)

    setattr(wizard, field.value, parsed)
    move_cursor_after_answer(wizard=wizard, field=field)

    return await _redraw(update=update, context=context)


def _to_int(raw_value: str) -> int | None:
    try:
        return int(raw_value)
    except ValueError:
        return None


def move_cursor_after_answer(wizard: ReminderWizard, field: ReminderField) -> None:
    """
    Dopo una risposta, decide dove va il cursore.

    La ricorrenza cambia la forma di `flow`, quindi riapre le domande anche se
    si stava modificando; gli altri campi, in modifica, tornano al riepilogo.
    """
    if field is ReminderField.RECURRENCE:
        wizard.editing = False
        wizard.advance_or_finish_wizard()
    elif wizard.editing:
        wizard.editing = False
        wizard.requesting = None
    else:
        wizard.advance_or_finish_wizard()
