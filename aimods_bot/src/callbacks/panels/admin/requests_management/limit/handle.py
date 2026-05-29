from datetime import timedelta, datetime, timezone
from enum import StrEnum
from typing import Literal, Union, Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode

from aimods_bot.src.core.customcontext import CustomContext, AdminLimitingUserRequests
from aimods_bot.src.core.pydantic import RequestSectionLimitation
from aimods_bot.src.helpers.constants.conversation_paths.navigation import GlobalAction, \
    AdminManageRequestLimitationsRoute
from aimods_bot.src.helpers.models.job_names import filter_jobs_by_kind, RequestLimitJobName
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.scheduler import schedule_request_limitation_deletion
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.utils.time_utils import parse_duration, timedelta_to_seconds
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)


def set_user_requests_limiting_item(
    context: CustomContext,
    set_true_section: Optional[RequestSection] = None,
) -> AdminLimitingUserRequests:
    wizard = context.pydc.persistent.limiting_user_requests
    if wizard is None:
        wizard = AdminLimitingUserRequests()
        context.pydc.persistent.limiting_user_requests = wizard
        if set_true_section:
            wizard.sections[set_true_section] = True
    return wizard


def get_request_limiting_detail(context: CustomContext, what: StrEnum):
    limiting_item = set_user_requests_limiting_item(context=context)
    return getattr(limiting_item, str(what))


def set_request_limiting_detail(
        context: CustomContext,
        what: Literal["user_id", "duration", "sections", "reason"],
        value: Union[str, int, dict]
):
    item = context.pydc.persistent.limiting_user_requests
    if item is None:
        log.warning("Key 'limit_user_requests' was not initialized.")
        return False

    setattr(item, what, value)


async def handle_request_limitation_duration(update: Update, context: CustomContext, duration_input: str):
    await safe_delete(update=update, context=context)

    item = context.pydc.persistent.limiting_user_requests

    if duration_input == AdminManageRequestLimitationsRoute.DURATION_ENDLESS:
        item.duration = 0
        return True

    parsed = parse_duration(duration_string=duration_input)

    effective_message = update.effective_message

    if not effective_message:
        raise ValueError("Attribute Update.effective_message cannot be None!")

    if not parsed:
        await effective_message.reply_text(
            text="⚠️ Indica una durata del tipo: <code>1 giorno 50 ore 2 minuti 10 secondi</code>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="🚮 Chiudi", callback_data=GlobalAction.CLOSE_MENU)]
            ]),
            parse_mode=ParseMode.HTML
        )
        return False

    item.duration = timedelta_to_seconds(parsed)
    return True


async def handle_request_limitation_topic(
        context: CustomContext,
        section_input: AdminManageRequestLimitationsRoute | RequestSection,
):
    item = context.pydc.persistent.limiting_user_requests

    if not item:
        raise ValueError("context.pydc.persistent.limiting_user_requests cannot be None here!")

    match section_input:
        case AdminManageRequestLimitationsRoute.BLOCK_ALL:
            for section in item.sections:
                item.sections[section] = True

        case AdminManageRequestLimitationsRoute.UNBLOCK_ALL:
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
        user_id: int,
        reason: str,
):
    await handle_limitation_reason(context=context, reason=reason)

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


async def handle_limitation_reason(context: CustomContext, reason: str):
    set_request_limiting_detail(context=context, what="reason", value=reason)


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
