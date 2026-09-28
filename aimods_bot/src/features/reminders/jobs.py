import html
from datetime import datetime, timezone

import telegram.error
from telegram import Bot
from telegram.constants import ParseMode

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import WrongTypeException
from aimods_bot.src.infra.log import logger
from aimods_bot.src.infra.scheduling.job_names import ReminderJobName
from aimods_bot.src.infra.scheduling.job_queue import schedule_unique_job
from aimods_bot.src.infra.scheduling.jobs import ReminderJob
from aimods_bot.src.features.reminders.models import Reminder
from aimods_bot.src.features.reminders.repository import get_reminder, register_execution
from aimods_bot.src.features.reminders.schedule import advance_past

log = logger.getChild(__name__)


async def deliver_reminder(bot: Bot, reminder: Reminder, recovery: bool = False) -> None:
    prefix = "🔁 <i>Promemoria recuperato</i>\n\n" if recovery else ""
    text = f"{prefix}⏰ <b>{html.escape(reminder.title)}</b>\n\n🔹 {html.escape(reminder.body)}"

    await bot.send_message(
        chat_id=reminder.chat_id,
        text=text,
        message_thread_id=reminder.thread_id,
        parse_mode=ParseMode.HTML,
    )


async def scheduled_send_reminder(context: CustomContext):
    """Invia, ricalcola, persiste e si ripianifica."""
    job = context.job
    if not job:
        raise ValueError("Job data must not be None here!")

    job_data = job.data
    if not isinstance(job_data, ReminderJob):
        raise WrongTypeException(job_data, "job_data", "ReminderJob")

    reminder = await get_reminder(job_data.reminder_id)
    if reminder is None:
        log.warning(f"Reminder {job_data.reminder_id} not in reminders table")
        return
    if not reminder.enabled:
        log.info(f"Reminder {reminder.id} disabled")
        return

    now = datetime.now(timezone.utc)

    try:
        await deliver_reminder(context.bot, reminder)
    except telegram.error.TelegramError as e:
        log.error(f"Sending reminder {reminder.id} failed: {e}")

    next_fire, _ = advance_past(reminder, now=max(now, reminder.next_fire))

    await register_execution(reminder.id, next_fire, last_fired_at=now)

    if next_fire is None:
        log.info(f"Reminder {reminder.id} one-shot, disabled in the database table")
        return

    schedule_unique_job(
        job_queue=context.job_queue,
        job_name=ReminderJobName(reminder_id=reminder.id),
        callback=scheduled_send_reminder,
        when=next_fire,
        data=ReminderJob(reminder_id=reminder.id),
    )
