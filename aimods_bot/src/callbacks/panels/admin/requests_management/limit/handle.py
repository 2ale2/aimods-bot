from datetime import timedelta, datetime, timezone

from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import RequestSectionLimitation
from aimods_bot.src.helpers.constants.path_navigation import LimitationsFlow
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.job_names import filter_jobs_by_kind, RequestLimitJobName
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.scheduler import schedule_request_limitation_deletion
from aimods_bot.src.helpers.utils.telegram_utils import render_error_panel

log = logger.getChild(__name__)


async def handle_request_limitation_topic(
        context: CustomContext,
        section_input: LimitationsFlow | RequestSection,
):
    item = context.get_or_create_limitation_wizard()

    if not item:
        raise ValueError("context.pydc.persistent.limiting_user_requests cannot be None here!")

    match section_input:
        case LimitationsFlow.BLOCK_ALL:
            for section in item.sections:
                item.sections[section] = True

        case LimitationsFlow.UNBLOCK_ALL:
            for section in item.sections:
                item.sections[section] = False

        case RequestSection() as section:
            item.sections[section] = not item.sections[section]

        case _:
            log.warning(f"Unexpected section_input: {section_input}")


def all_sections_are(context: CustomContext, what: bool):
    item = context.pydc.persistent.limiting_user_requests

    if not item:
        raise ValueError("context.pydc.persistent.limiting_user_requests cannot be None here!")

    sections = item.sections
    return all(bool_value == what for bool_value in sections.values())


async def handle_limitation_confirmation(
        update: Update,
        context: CustomContext,
        user_id: int
):
    new_limitations = get_request_limitations(update=update, context=context)
    current_limitations = context.get_user_request_limitations(user_id=user_id) or []

    effective_user = update.effective_user
    if not effective_user:
        raise ValueError("Attribute Update.effective_user cannot be None here!")

    admin_id = effective_user.id
    now = datetime.now(timezone.utc)

    current_by_section = {l.section: l for l in current_limitations}
    new_by_section = {l.section: l for l in new_limitations}

    merged: list[RequestSectionLimitation] = []

    for key, existing in current_by_section.items():
        new = new_by_section.get(key)

        if new is None:
            merged.append(existing)
            continue

        if existing.until is None or new.until is None:
            merged_until = None
        else:
            merged_until = existing.until + (new.until - now)

        merged.append(RequestSectionLimitation(
            section=existing.section,
            until=merged_until,
            reasons=[*existing.reasons, *new.reasons],
            created_by=existing.created_by,
            created_at=existing.created_at,
            updated_by=admin_id
        ))

    for key, new in new_by_section.items():
        if key not in current_by_section:
            merged.append(new)

    for job in filter_jobs_by_kind(
        job_queue=context.job_queue,
        name_type=RequestLimitJobName,
        predicate=lambda n: n.user_id == user_id,
    ):
        job.schedule_removal()

    for limitation in merged:
        if limitation.until is None:
            continue
        await schedule_request_limitation_deletion(
            context=context,
            user_id=user_id,
            section=limitation.section,
            until=limitation.until
        )

    context.set_user_request_limitations(user_id=user_id, limitations=merged)


def get_request_limitations(update: Update, context: CustomContext) -> list[RequestSectionLimitation]:
    wizard = context.get_or_create_limitation_wizard()
    duration = wizard.duration
    reason = wizard.reason
    sections = wizard.sections

    if duration:
        duration_delta = timedelta(seconds=duration)
        until = datetime.now(timezone.utc) + duration_delta
    else:
        until = None

    effective_user = update.effective_user
    if not effective_user:
        raise ValueError("Attribute Update.effective_user cannot be None here!")

    limitations = []
    for section in sections:
        if sections[section]:
            limitations.append(RequestSectionLimitation(
                section=section,
                until=until,
                reasons=[reason],
                created_by=effective_user.id,
                updated_by=effective_user.id
            ))

    return limitations


async def handle_remove_user_request_limitation(
        update: Update,
        context: CustomContext,
        user_id: int,
        selected_section: LimitationsFlow | RequestSection
):
    """Rimuove le limitazioni dell'utente."""
    if selected_section == LimitationsFlow.REMOVE_ALL:
        _remove_limitation_jobs(context, user_id, section_pattern=r"[^:\s]+")

        context.set_user_request_limitations(user_id=user_id, limitations=[])
        log.info(f"Admin {context.user_id} removed all section limitations for {user_id}.")
        return

    current_limitations = context.get_user_request_limitations(user_id=user_id)

    if current_limitations is None:
        log.warning(f"User {user_id} has no limitations")
        await render_error_panel(
            update=update,
            context=context,
            text="⚠️ L'utente non ha limitazioni attive. È possibile che un altro admin abbia rimosso questa "
                 "limitazione nel frattempo."
        )
        return

    new_limitations = [lim for lim in current_limitations if lim.section != selected_section]

    if len(new_limitations) == len(current_limitations):
        return

    context.set_user_request_limitations(user_id=user_id, limitations=new_limitations)

    _remove_limitation_jobs(context, user_id, section_pattern=str(selected_section))

    log.info(f"Admin {context.user_id} removed {selected_section} section limitations from {user_id}")


def _remove_limitation_jobs(context: CustomContext, user_id: int, section_pattern: str):
    """Rimuove i job schedulati che corrispondono al pattern."""
    job_name_pattern = rf"^request_limit:{user_id}:{section_pattern}$"
    # noinspection PyUnresolvedReferences
    jobs = context.job_queue.get_jobs_by_name(job_name_pattern)

    for job in jobs:
        log.info(f"Removing scheduled job {job.name} for user {user_id}")
        job.schedule_removal()
