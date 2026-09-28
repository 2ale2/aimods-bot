from datetime import datetime, timezone

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode

from aimods_bot.src.callbacks.panels.admin.tools.reminder.render import render_reminder_wizard_step, \
    render_admin_reminder_tool_panel, render_reminder_created_panel, render_manage_reminders_list_panel, \
    render_reminder_card_panel
from aimods_bot.src.core.customcontext import ReminderWizard, CustomContext
from aimods_bot.src.core.constants import ReminderField, Recurrence
from aimods_bot.src.ui.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.ui.path_navigation import GlobalAction
from aimods_bot.src.ui.path_navigation.admin import ReminderRoute
from aimods_bot.src.infra.scheduling.job_queue import schedule_unique_job, scheduled_send_reminder, remove_job
from aimods_bot.src.infra.log import logger
from aimods_bot.src.infra.scheduling.job_names import ReminderJobName
from aimods_bot.src.infra.scheduling.jobs import ReminderJob
from aimods_bot.src.features.reminders.models import LAST_DAY_OF_MONTH, Reminder
from aimods_bot.src.ui.routing import PathBuilder
from aimods_bot.src.helpers.reminders_utils import create_reminder, get_reminder, delete_reminder, toggle_reminder, \
    reschedule_reminder, update_reminder
from aimods_bot.src.helpers.utils.reminder_time_utils import advance_past
from aimods_bot.src.infra.telegram.utils import safe_delete
from aimods_bot.src.shared.text_utils import to_int
from aimods_bot.src.shared.time_utils import parse_clock_time, parse_absolute_datetime, is_nonexistent_local_time

log = logger.getChild(__name__)

# Il singolo messaggio in ingresso può arrivare a 4096 caratteri, ma
# `deliver_reminder` compone prefisso + titolo + corpo e `html.escape` gonfia:
# senza un tetto qui, un promemoria valido in bozza fallisce all'invio, dove
# nessuno lo vede. Resta scoperto il caso patologico (un corpo di soli `&`
# sestuplica) — quello è il fallimento d'invio, che vuole il canale di log.
_FIELD_MAX_LENGTH: dict[ReminderField, int] = {
    ReminderField.TITLE: 200,
    ReminderField.BODY: 3000,
}


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
            days = to_int(raw_value)
            if days is None or days < 1:
                return False
            wizard.interval_days = days
            return True

        case ReminderField.DAY_OF_WEEK:
            day = to_int(raw_value)
            if day is None or not 0 <= day <= 6:  # 0 = lunedì
                return False
            wizard.day_of_week = day
            return True

        case ReminderField.DAY_OF_MONTH:
            day = to_int(raw_value)
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
            [InlineKeyboardButton(text="🚮 Chiudi", callback_data=GlobalAction.CLOSE)]
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
        return PCS.ADMIN_CONVERSATION

    field = wizard.requesting
    if not raw:
        return await _reject(update, context, "⚠️ Il testo non può essere vuoto.", PCS.SET_REMINDER_BODY)

    limit = _FIELD_MAX_LENGTH[field]
    if len(raw) > limit:
        return await _reject(
            update, context,
            f"⚠️ Troppo lungo: massimo <b>{limit}</b> caratteri, ne hai scritti <b>{len(raw)}</b>.",
            PCS.SET_REMINDER_BODY
        )

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


async def handle_reminder_confirm(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
) -> int:
    """
    Valida la bozza, la persiste, pianifica il job e pulisce.

    Pianifica subito invece di aspettare `_reschedule_reminders()` al boot:
    un promemoria creato e non pianificato è indistinguibile da uno pianificato
    finché non manca l'invio.
    """
    wizard = context.pydc.persistent.active_reminder_wizard
    menu_path = base_path.back()

    if wizard is None:
        # Bottone vecchio su una bozza già confermata o annullata.
        await render_admin_reminder_tool_panel(update=update, context=context, base_path=menu_path)
        return PCS.ADMIN_CONVERSATION

    is_edit = wizard.reminder_id is not None
    original: Reminder | None = None

    if is_edit:
        original = await get_reminder(wizard.reminder_id)
        if original is None:
            # Eliminato mentre lo si modificava, magari da un altro admin.
            log.warning(f"Confirm on reminder {wizard.reminder_id}, gone from the table")
            context.clear_reminder_wizard()
            context.clear_saved_path()
            context.pydc.persistent.bot_message_id = None
            await update.callback_query.answer(
                text="⚠️ Questo promemoria non esiste più: la modifica è stata annullata.",
                show_alert=True
            )
            await render_admin_reminder_tool_panel(update=update, context=context, base_path=menu_path)
            return PCS.ADMIN_CONVERSATION

        chat_id = original.chat_id
        created_by = original.created_by
    else:
        chat_id = context.pydb.staff_chat_id
        created_by = update.effective_user.id

        if chat_id is None:
            log.error("STAFF_CHAT_ID not configured: cannot create reminder.")
            await update.callback_query.answer(
                text="⚠️ Il gruppo staff non è configurato.",
                show_alert=True
            )
            return PCS.ADMIN_CONVERSATION

    try:
        reminder = wizard.to_reminder(chat_id=chat_id, created_by=created_by)
    except ValueError as e:
        # Conferma premuta su una bozza incompleta: bottone rimasto in un messaggio vecchio.
        # Non è un errore da mostrare, è un redraw: il wizard riapre il campo mancante.
        log.warning(f"Confirm on incomplete reminder draft: {e}")
        return await render_reminder_wizard_step(
            update=update,
            context=context,
            base_path=base_path,
            wizard=wizard
        )

    # `misfire_grace_time` vale 1 secondo: un job pianificato nel passato viene
    # scartato in silenzio. La validazione di ONCE_AT avviene quando l'admin
    # *scrive* la data, non quando *conferma* — e in modifica la data arriva
    # già scritta, da prima. Senza questo controllo si legge "creato" e non
    # succede nulla fino al riavvio.
    if reminder.next_fire <= datetime.now(timezone.utc):
        await update.callback_query.answer(
            text="⚠️ Quella data è ormai passata. Indica un nuovo momento.",
            show_alert=True
        )
        if reminder.recurrence is Recurrence.ONCE:
            wizard.requesting = ReminderField.ONCE_AT
            wizard.editing = True
        else:
            log.error(f"Recurring reminder computed a past next_fire: {reminder.next_fire}")
        return await render_reminder_wizard_step(
            update=update,
            context=context,
            base_path=base_path,
            wizard=wizard
        )

    if is_edit:
        # La modifica cambia il contenuto, non lo stato: un promemoria sospeso
        # resta sospeso anche dopo che ne è stato corretto il testo.
        reminder.enabled = original.enabled

        if not await update_reminder(reminder):
            await update.callback_query.answer(
                text="❌ Aggiornamento nel database non riuscito. La bozza è ancora qui, riprova.",
                show_alert=True
            )
            return PCS.ADMIN_CONVERSATION
    else:
        reminder_id = await create_reminder(reminder)
        if reminder_id is None:
            await update.callback_query.answer(
                text="❌ Inserimento nel database non riuscito. La bozza è ancora qui, riprova.",
                show_alert=True
            )
            return PCS.ADMIN_CONVERSATION

        reminder.id = reminder_id

    if reminder.enabled:
        schedule_unique_job(
            job_queue=context.job_queue,
            job_name=ReminderJobName(reminder_id=reminder.id),
            callback=scheduled_send_reminder,
            when=reminder.next_fire,
            data=ReminderJob(reminder_id=reminder.id)
        )
    else:
        remove_job(job_queue=context.job_queue, job_name=ReminderJobName(reminder_id=reminder.id))

    context.clear_reminder_wizard()
    context.clear_saved_path()
    context.pydc.persistent.bot_message_id = None

    await render_reminder_created_panel(
        update=update,
        context=context,
        base_path=menu_path,
        reminder=reminder,
        updated=is_edit
    )
    return PCS.ADMIN_CONVERSATION


async def handle_reminder_toggle(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        reminder_id: int
) -> int:
    """Sospende o riattiva. `base_path` è la gestione."""
    reminder = await get_reminder(reminder_id)

    if reminder is None:
        if update.callback_query:
            await update.callback_query.answer(
                text="⚠️ Questo promemoria non esiste più.",
                show_alert=True
            )
        await render_manage_reminders_list_panel(
            update=update, context=context, base_path=base_path
        )
        return PCS.ADMIN_CONVERSATION

    job_name = ReminderJobName(reminder_id=reminder_id)

    if reminder.enabled:
        if not await toggle_reminder(reminder_id, False):
            await update.callback_query.answer(text="❌ Operazione non riuscita.", show_alert=True)
            return PCS.ADMIN_CONVERSATION
        remove_job(job_queue=context.job_queue, job_name=job_name)
        log.info(f"Reminder {reminder_id} suspended by {update.effective_user.id}")

        await render_reminder_card_panel(
            update=update, context=context, base_path=base_path, reminder_id=reminder_id
        )
        return PCS.ADMIN_CONVERSATION

    next_fire, _ = advance_past(reminder, now=datetime.now(timezone.utc))

    if next_fire is None:
        await update.callback_query.answer(
            text="⚠️ È un promemoria una tantum e la sua data è passata. "
                 "Modificalo indicando un nuovo momento, poi riattivalo.",
            show_alert=True
        )
        return PCS.ADMIN_CONVERSATION

    if next_fire != reminder.next_fire and not await reschedule_reminder(reminder_id=reminder_id, next_fire=next_fire):
        await update.callback_query.answer(text="❌ Operazione non riuscita.", show_alert=True)
        return PCS.ADMIN_CONVERSATION

    if not await toggle_reminder(reminder_id, True):
        await update.callback_query.answer(text="❌ Operazione non riuscita.", show_alert=True)
        return PCS.ADMIN_CONVERSATION

    schedule_unique_job(
        job_queue=context.job_queue,
        job_name=job_name,
        callback=scheduled_send_reminder,
        when=next_fire,
        data=ReminderJob(reminder_id=reminder_id)
    )
    log.info(f"Reminder {reminder_id} resumed by {update.effective_user.id}, next fire {next_fire}")

    await render_reminder_card_panel(
        update=update,
        context=context,
        base_path=base_path,
        reminder_id=reminder_id
    )

    return PCS.ADMIN_CONVERSATION


async def handle_reminder_delete(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        reminder_id: int
) -> int:
    """Elimina definitivamente. `base_path` è la gestione."""
    remove_job(job_queue=context.job_queue, job_name=ReminderJobName(reminder_id=reminder_id))

    if not await delete_reminder(reminder_id):
        await update.callback_query.answer(text="❌ Eliminazione non riuscita.", show_alert=True)
        await render_reminder_card_panel(
            update=update,
            context=context,
            base_path=base_path,
            reminder_id=reminder_id
        )
        return PCS.ADMIN_CONVERSATION

    log.info(f"Reminder {reminder_id} deleted by {update.effective_user.id}")

    wizard = context.pydc.persistent.active_reminder_wizard
    if wizard is not None and wizard.reminder_id == reminder_id:
        context.clear_reminder_wizard()
        context.clear_saved_path()
        context.pydc.persistent.bot_message_id = None

    await update.callback_query.answer(text="🗑 Promemoria eliminato.")

    await render_manage_reminders_list_panel(
        update=update,
        context=context,
        base_path=base_path
    )

    return PCS.ADMIN_CONVERSATION


async def handle_reminder_edit_start(
        update: Update,
        context: CustomContext,
        draft_path: PathBuilder,
        manage_path: PathBuilder,
        reminder_id: int
) -> int:
    """
    Apre il wizard su un promemoria esistente, direttamente sul riepilogo.

    Il cursore parte da fermo (`requesting = None`)
    """
    reminder = await get_reminder(reminder_id)

    if reminder is None:
        if update.callback_query:
            await update.callback_query.answer(
                text="⚠️ Questo promemoria non esiste più.",
                show_alert=True
            )
        await render_manage_reminders_list_panel(
            update=update,
            context=context,
            base_path=manage_path
        )
        return PCS.ADMIN_CONVERSATION

    previous = context.pydc.persistent.active_reminder_wizard
    replacing = previous is not None and previous.reminder_id != reminder_id

    wizard = context.get_or_create_reminder_wizard(source=reminder)
    wizard.requesting = None
    wizard.editing = False

    if replacing and update.callback_query:
        await update.callback_query.answer(text="ℹ️ La bozza precedente è stata sostituita.")

    return await render_reminder_wizard_step(
        update=update,
        context=context,
        base_path=draft_path,
        wizard=wizard
    )
