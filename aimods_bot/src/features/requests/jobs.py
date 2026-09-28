from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import WrongTypeException
from aimods_bot.src.infra.scheduling.jobs import RemoveCompletedRequestJob, RemoveRequestCooldownJob, \
    RemoveSectionLimitationJob, SectionOpeningCheckJob
from aimods_bot.src.features.requests.notifications import send_opening_notifications


async def scheduled_remove_completed_requests(context: CustomContext):
    job = context.job
    if not job:
        raise ValueError("Job data must not be None here!")

    job_data = context.job.data
    if not isinstance(job_data, RemoveCompletedRequestJob):
        raise WrongTypeException(job_data, "job_data", "RemoveCompletedRequestJob")

    request_id = job_data.request_id
    context.remove_from_active_requests(ix=request_id)


async def scheduled_remove_user_request_cooldown(context: CustomContext):
    job = context.job
    if not job:
        raise ValueError("Job data must not be None here!")

    job_data = context.job.data
    if not isinstance(job_data, RemoveRequestCooldownJob):
        raise WrongTypeException(job_data, "job_data", "RemoveRequestCooldownJob")

    context.remove_user_request_cooldown(user_id=job_data.user_id)


async def scheduled_remove_user_request_section_limitation(context: CustomContext):
    job = context.job
    if not job:
        raise ValueError("Job data must not be None here!")

    job_data = context.job.data
    if not isinstance(job_data, RemoveSectionLimitationJob):
        raise WrongTypeException(job_data, "job_data", "RemoveSectionLimitationJob")

    current = context.get_user_request_limitations(user_id=job_data.user_id)
    if not current:
        return

    remaining = [
        x for x in current
        if not (x.section.platform == job_data.section.platform and x.section.category == job_data.section.category)
    ]
    context.set_user_request_limitations(user_id=job_data.user_id, limitations=remaining)


async def scheduled_section_opening_check_for_user_notification(context: CustomContext):
    job = context.job
    if not job:
        raise ValueError("Job data must not be None here!")

    job_data = context.job.data
    if not isinstance(job_data, SectionOpeningCheckJob):
        raise WrongTypeException(job_data, "job_data", "SectionOpeningCheckJob")

    if context.is_request_section_open(section=job_data.section):
        await send_opening_notifications(context=context, section=job_data.section)
