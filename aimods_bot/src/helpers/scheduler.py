from datetime import datetime
from typing import Optional, Any, Callable

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import JobInfo
from aimods_bot.src.helpers.job_queue import scheduled_remove_user_request_section_limitation, \
    scheduled_remove_request_cooldown, scheduled_section_opening_check_for_user_notification
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.time_utils import ensure_utc

log = logger.getChild(__name__)


# ========== HELPER INTERNI ==========

def _schedule_unique_job(
    context: CustomContext,
    job_name: str,
    callback: Callable,
    when: datetime | float | int,
    data: Any
):
    """
    Rimuove eventuali job esistenti con lo stesso nome e ne schedula uno nuovo.
    """
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for j in current_jobs:
        j.schedule_removal()
        log.debug(f"Job precedente rimosso: {job_name}")

    context.job_queue.run_once(
        callback=callback,
        when=when,
        data=data,
        name=job_name
    )


async def schedule_request_limitation_deletion(
        context: CustomContext,
        user_id: int,
        section: str,
        until: Optional[datetime]
):
    if until is None:
        return

    until_utc = ensure_utc(until)
    job_name = f"request_limit:{user_id}:{section}"

    _schedule_unique_job(
        context=context,
        job_name=job_name,
        callback=scheduled_remove_user_request_section_limitation,
        when=until_utc,
        data={"user_id": user_id, "section": section}
    )

    context.pydb.jobs[job_name] = JobInfo(
        next_date=until_utc.isoformat(),
        executed=False
    )

    log.info(f"Scheduled {job_name} for {user_id} section {section}")


async def schedule_request_cooldown_removal(context: CustomContext, user_id: int, until: datetime):
    until_utc = ensure_utc(until)
    job_name = f"request_cooldown:{user_id}"

    _schedule_unique_job(
        context=context,
        job_name=job_name,
        callback=scheduled_remove_request_cooldown,
        when=until_utc,
        data={"user_id": user_id}
    )

    context.pydb.jobs[job_name] = JobInfo(
        next_date=until_utc.isoformat(),
        executed=False
    )


async def schedule_section_opening_check_for_user_notification(context: CustomContext, section: str):
    job_name = f"delayed_section_opening_check:{section}"

    _schedule_unique_job(
        context=context,
        job_name=job_name,
        callback=scheduled_section_opening_check_for_user_notification,
        when=10,
        data={"section": section}
    )
