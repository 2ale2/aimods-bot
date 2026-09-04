from aimods_bot.src.core.customcontext import ReminderWizard
from aimods_bot.src.helpers.constants.constants import ReminderField, Recurrence
from aimods_bot.src.helpers.constants.path_navigation.admin import ReminderRoute
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.reminders import LAST_DAY_OF_MONTH

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
            if day is None or not 0 <= day <= 6:  # 0 = lunedì, convenzione Python
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
