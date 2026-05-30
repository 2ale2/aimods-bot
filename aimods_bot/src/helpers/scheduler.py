from datetime import datetime
from typing import Optional, Any, Callable

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import JobInfo
from aimods_bot.src.helpers.job_queue import scheduled_remove_user_request_section_limitation, \
    scheduled_remove_user_request_cooldown, scheduled_section_opening_check_for_user_notification
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.job_names import RequestLimitJobName, RequestCooldownJobName, \
    DelayedSectionOpeningJobName, JobName
from aimods_bot.src.helpers.models.jobs import RemoveSectionLimitationJob, RemoveRequestCooldownJob, \
    SectionOpeningCheckJob
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.utils.time_utils import ensure_utc

log = logger.getChild(__name__)


# ========== HELPER INTERNI ==========

def _schedule_unique_job(
        context: CustomContext,
        job_name: JobName,
        callback: Callable,
        when: datetime | float | int,
        data: Any,
):
    """Rimuove eventuali job esistenti con lo stesso nome e ne schedula uno nuovo."""
    job_queue = context.job_queue
    if job_queue is None:
        raise ValueError("Job Queue must not be None!")

    name_str = str(job_name)

    for j in job_queue.get_jobs_by_name(name_str):
        j.schedule_removal()
        log.debug(f"Job precedente rimosso: {name_str}")

    job = job_queue.run_once(
        callback=callback,
        when=when,
        data=data,
        name=name_str,
    )
    return job


async def schedule_request_limitation_deletion(
        context: CustomContext,
        user_id: int,
        section: RequestSection,
        until: Optional[datetime]
):
    if until is None:
        return

    until_utc = ensure_utc(until)
    job_name = RequestLimitJobName(user_id=user_id, section=section)

    job = _schedule_unique_job(
        context=context,
        job_name=job_name,
        callback=scheduled_remove_user_request_section_limitation,
        when=until_utc,
        data=RemoveSectionLimitationJob(user_id=user_id, section=section),
    )

    context.pydb.jobs[str(job_name)] = JobInfo(next_date=job.next_t)

    log.info(f"Scheduled limitation removal for user {user_id} section {section} at {until_utc.isoformat()}")


async def schedule_request_cooldown_removal(context: CustomContext, user_id: int, until: datetime):
    until_utc = ensure_utc(until)
    job_name = RequestCooldownJobName(user_id=user_id)

    job = _schedule_unique_job(
        context=context,
        job_name=job_name,
        callback=scheduled_remove_user_request_cooldown,
        when=until_utc,
        data=RemoveRequestCooldownJob(user_id=user_id),
    )

    context.pydb.jobs[str(job_name)] = JobInfo(next_date=job.next_t)

    log.info(f"Scheduled cooldown removal for user {user_id} at {until_utc.isoformat()}")


async def schedule_section_opening_check_for_user_notification(
        context: CustomContext,
        section: RequestSection
):
    job_name = DelayedSectionOpeningJobName(section=section)

    job = _schedule_unique_job(
        context=context,
        job_name=job_name,
        callback=scheduled_section_opening_check_for_user_notification,
        when=10,
        data=SectionOpeningCheckJob(section=section),
    )

    context.pydb.jobs[str(job_name)] = JobInfo(next_date=job.next_t)
