from datetime import timedelta, datetime, timezone
from typing import Literal, Union

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode

from aimods_bot.src.core.customcontext import CustomContext, AdminLimitingUserRequests
from aimods_bot.src.core.pydantic import RequestSectionLimitation
from aimods_bot.src.helpers.scheduler import schedule_request_limitation_deletion
from aimods_bot.src.helpers.utils.time_utils import parse_duration, timedelta_to_seconds
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("handle_request_limitation")


def set_user_requests_limiting_item(context: CustomContext):
    """Crea la struttura dati nella persistenza, se non è presente; ritorna la struttura."""
    if context.pydc.persistent.limiting_user_requests is None:
        context.pydc.persistent.limiting_user_requests = AdminLimitingUserRequests()

    return context.pydc.persistent.limiting_user_requests


def get_request_limiting_detail(context: CustomContext, what: Literal["user_id", "duration", "sections", "reason"]):
    limiting_item = set_user_requests_limiting_item(context=context)
    return getattr(limiting_item, what)


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


async def handle_request_limitation_duration(update: Update, context: CustomContext):
    item = context.pydc.persistent.limiting_user_requests
    if update.callback_query and update.callback_query.data.endswith("endless"):
        item.duration = 0
        return True

    text = update.effective_message.text
    parsed = parse_duration(duration_string=text)

    if not parsed:
        await update.effective_message.reply_text(
            text="⚠️ Indica una durata del tipo: <code>1 giorno 50 ore 2 minuti 10 secondi</code>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="🚮 Chiudi", callback_data="close_menu")]
            ]),
            parse_mode=ParseMode.HTML
        )
        return False

    item.duration = timedelta_to_seconds(parsed)
    return True


async def handle_request_limitation_topic(update: Update, context: CustomContext):
    data = update.callback_query.data.split("/")[-1]
    item = context.pydc.persistent.limiting_user_requests
    sections = item.sections

    if data in ("block_all", "unblock_all"):
        flag = (data == "block_all")
        for cats in sections.values():
            for k in cats:
                cats[k] = flag
    else:
        platform_str, category_str = data.split("-")
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


async def handle_limitation_confirmation(update: Update, context: CustomContext):
    await handle_limitation_reason(update=update, context=context)

    user_id = get_request_limiting_detail(context=context, what="user_id")

    new_limitations = get_request_limitations(update=update, context=context)
    current_limitations = context.get_user_request_limitations(user_id=user_id)

    if current_limitations:
        new_map = {el.section: {"until": el.until, "reason": el.reasons} for el in new_limitations}
        current_map = {
            el.section: {"until": el.until, "reason": el.reasons, "updated": False} for el in current_limitations
        }
        for section in new_map:
            if section in current_map:
                nu = new_map[section]["until"]
                cu = current_map[section]["until"]
                if nu is None or cu is None:
                    current_map[section]["until"] = None
                else:
                    current_map[section]["until"] = cu + (nu - datetime.now(timezone.utc))
                current_map[section]["reason"].extend(new_map[section]["reason"])
                current_map[section]["updated"] = True
            else:
                current_map[section] = {
                    "until": new_map[section]["until"],
                    "reason": new_map[section]["reason"]
                }

        total_limitations = []
        for l in current_limitations:
            map_item = current_map[l.section]
            updated = current_map[l.section]["updated"]
            total_limitations.append(RequestSectionLimitation(
                section=l.section,
                until=map_item["until"],
                reasons=map_item["reason"],
                created_by=l.created_by if updated else update.effective_user.id,
                created_at=l.created_at if updated else None,  # default: now(utc)
                updated_by=update.effective_user.id,
                updated_at=None  # default: now(utc)
            ))
    else:
        total_limitations = new_limitations

    for limitation in total_limitations:
        if limitation.until is not None:
            await schedule_request_limitation_deletion(
                context=context,
                user_id=user_id,
                section=limitation.section,
                until=limitation.until
            )

    context.set_user_request_limitations(user_id=user_id, limitations=total_limitations)


async def handle_limitation_reason(update: Update, context: CustomContext):
    set_request_limiting_detail(context=context, what="reason", value=update.effective_message.text)


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
    for pl in sections:
        for ca in sections[pl]:
            if sections[pl][ca]:
                limitations.append(RequestSectionLimitation(
                    section=f"{pl}:{ca}",
                    until=until,
                    reasons=[reason],
                    created_by=update.effective_user.id,
                    updated_by=update.effective_user.id
                ))

    return limitations
