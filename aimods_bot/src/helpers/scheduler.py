from datetime import datetime
from typing import Optional

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.job_queue import scheduled_remove_user_request_section_limitation, \
    scheduled_remove_request_cooldown, scheduled_section_opening_check_for_user_notification
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)


async def schedule_request_limitation_deletion(
        context: CustomContext,
        user_id: int,
        section: str,
        until: Optional[datetime]
):
    if until is None:
        return

    job_name = f"request_limit:{user_id}:{section}"
    for j in context.job_queue.get_jobs_by_name(job_name):
        log.info(f"Removed {job_name} for {user_id} section {section}")
        j.schedule_removal()

    context.job_queue.run_once(
        callback=scheduled_remove_user_request_section_limitation,
        when=until,
        data={"user_id": user_id, "section": section},
        name=job_name
    )

    log.info(f"Scheduled {job_name} for {user_id} section {section}")


async def schedule_request_cooldown_removal(context: CustomContext, user_id: int, until: datetime):
    job_name = f"request_cooldown:{user_id}"
    for j in context.job_queue.get_jobs_by_name(job_name):
        j.schedule_removal()

    context.job_queue.run_once(
        callback=scheduled_remove_request_cooldown,
        when=until,
        data={"user_id": user_id},
        name=job_name
    )


async def schedule_section_opening_check_for_user_notification(context: CustomContext, section: str):
    job_name = f"delayed_section_opening_check:{section}"
    for j in context.job_queue.get_jobs_by_name(job_name):
        j.schedule_removal()

    context.job_queue.run_once(
        callback=scheduled_section_opening_check_for_user_notification,
        when=10,
        data={"section": section},
        name=job_name
    )
