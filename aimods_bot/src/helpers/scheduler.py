from datetime import datetime

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.job_queue import scheduled_remove_user_request_section_limitation


async def schedule_request_limitation_deletion(context: CustomContext, user_id: int, section: str, until: datetime):
    if until is None:
        return

    job_name = f"request_limit:{user_id}:{section}"
    for j in context.job_queue.get_jobs_by_name(job_name):
        j.schedule_removal()

    context.job_queue.run_once(
        callback=scheduled_remove_user_request_section_limitation,
        when=until,
        data={"user_id": user_id, "section": section},
        name=job_name
    )
