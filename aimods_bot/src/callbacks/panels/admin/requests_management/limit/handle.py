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
from aimods_bot.src.helpers.scheduler import schedule_request_limitation_deletion
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.utils.time_utils import parse_duration, timedelta_to_seconds
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)


def set_user_requests_limiting_item(context: CustomContext, set_true_section: Optional[str] = None):
    """Crea la struttura dati nella persistenza, se non è presente; ritorna la struttura."""
    if context.pydc.persistent.limiting_user_requests is None:
        context.pydc.persistent.limiting_user_requests = AdminLimitingUserRequests()
        if set_true_section:
            pl, ca = set_true_section.split(":")
            platform = context.pydc.persistent.limiting_user_requests.sections.get(pl, None)
            if ca in platform:
                context.pydc.persistent.limiting_user_requests.sections[pl][ca] = True
            else:
                log.warning(f"Section {set_true_section} not found")

    return context.pydc.persistent.limiting_user_requests


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

    if not parsed:
        await update.effective_message.reply_text(
            text="⚠️ Indica una durata del tipo: <code>1 giorno 50 ore 2 minuti 10 secondi</code>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="🚮 Chiudi", callback_data=GlobalAction.CLOSE_MENU)]
            ]),
            parse_mode=ParseMode.HTML
        )
        return False

    item.duration = timedelta_to_seconds(parsed)
    return True


async def handle_request_limitation_topic(update: Update, context: CustomContext, section_input: str):
    item = context.pydc.persistent.limiting_user_requests
    sections = item.sections

    if section_input in (AdminManageRequestLimitationsRoute.BLOCK_ALL, AdminManageRequestLimitationsRoute.UNBLOCK_ALL):
        flag = (section_input == AdminManageRequestLimitationsRoute.BLOCK_ALL)
        for cats in sections.values():
            for k in cats:
                cats[k] = flag
    else:
        platform_str, category_str = section_input.split("-")
        cats = sections.get(platform_str)
        cats[category_str] = not cats[category_str]

    # opzionale: trigger valida/persistenza
    item.sections = sections


def all_sections_are(context: CustomContext, what: bool):
    sections = context.pydc.persistent.limiting_user_requests.sections
    for platform, categories in sections.items():
        for category in categories:
            if sections[platform][category] != what:
                return False
    return True


async def handle_limitation_confirmation(
        update: Update,
        context: CustomContext,
        user_id: int,
        reason: str,
):
    await handle_limitation_reason(update=update, context=context, reason=reason)

    new_limitations = get_request_limitations(update=update, context=context)
    current_limitations = context.get_user_request_limitations(user_id=user_id) or []

    admin_id = update.effective_user.id
    now = datetime.now(timezone.utc)

    current_by_section = {(l.platform, l.category): l for l in current_limitations}
    new_by_section = {(l.platform, l.category): l for l in new_limitations}

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
            platform=existing.platform,
            category=existing.category,
            until=merged_until,
            reasons=[*existing.reasons, *new.reasons],
            created_by=existing.created_by,
            created_at=existing.created_at,
            updated_by=admin_id,
        ))

    for key, new in new_by_section.items():
        if key not in current_by_section:
            merged.append(new)

    for job in filter_jobs_by_kind(
        context.job_queue,
        RequestLimitJobName,
        lambda n: n.user_id == user_id,
    ):
        job.schedule_removal()

    for limitation in merged:
        if limitation.until is None:
            continue
        await schedule_request_limitation_deletion(
            context=context,
            user_id=user_id,
            platform=limitation.platform,
            category=limitation.category,
            until=limitation.until,
        )

    context.set_user_request_limitations(user_id=user_id, limitations=merged)


async def handle_limitation_reason(update: Update, context: CustomContext, reason: str):
    set_request_limiting_detail(context=context, what="reason", value=reason)


def get_request_limitations(update: Update, context: CustomContext) -> list[RequestSectionLimitation]:
    sections = get_request_limiting_detail(context=context, what="sections")
    duration = get_request_limiting_detail(context=context, what="duration")
    reason = get_request_limiting_detail(context=context, what="reason")

    if duration:
        duration_delta = timedelta(seconds=duration)
        until = datetime.now(timezone.utc) + duration_delta
    else:
        until = None

    limitations = []
    for platform in sections:
        for category in sections[platform]:
            if sections[platform][category]:
                limitations.append(RequestSectionLimitation(
                    platform=platform,
                    category=category,
                    until=until,
                    reasons=[reason],
                    created_by=update.effective_user.id,
                    updated_by=update.effective_user.id
                ))

    return limitations
