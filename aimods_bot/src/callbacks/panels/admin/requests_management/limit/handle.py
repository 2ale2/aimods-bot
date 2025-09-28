from datetime import timedelta, datetime, timezone
from typing import Literal, Union

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import RequestSectionLimitation
from aimods_bot.src.helpers.constants.constants import CATEGORY_DETAILS
from aimods_bot.src.helpers.scheduler import schedule_request_limitation_deletion
from aimods_bot.src.helpers.utils.time_utils import parse_duration, timedelta_to_seconds
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("handle_request_limitation")


def set_user_requests_limiting_item(context: CustomContext):
    """Crea la struttura dati nella persistenza, se non è presente; ritorna la struttura."""
    sections = {}
    for platform, categories in CATEGORY_DETAILS.items():
        sections[platform] = {}
        for category in categories:
            if context.pyd.base_path and f"{platform}/{category}" in context.pyd.base_path:
                sections[platform][category] = True
            else:
                sections[platform][category] = False

    return context.chat_data.setdefault("limit_user_requests", {
        "user_id": 0,
        "duration": 0,
        "sections": sections,
        "reason": ""
    })


def get_request_limiting_detail(context: CustomContext, what: Literal["user_id", "duration", "sections", "reason"]):
    limiting_item = set_user_requests_limiting_item(context=context)
    return limiting_item[what]


def set_request_limiting_detail(
        context: CustomContext,
        what: Literal["user_id", "duration", "sections", "reason"],
        value: Union[str, int, dict]
):
    item = context.chat_data.get("limit_user_requests", None)
    if item is None:
        log.warning("Key 'limit_user_requests' was not found.")
        return False

    context.chat_data["limit_user_requests"][what] = value


async def handle_request_limitation_duration(update: Update, context: CustomContext):
    if update.callback_query and update.callback_query.data.endswith("endless"):
        context.chat_data["limit_user_requests"]["duration"] = 0
        return True

    text = update.effective_message.text
    parsed = parse_duration(duration_string=text)

    if not parsed:
        await update.effective_message.reply_text(
            text="⚠️ Indica una durata del tipo: <code>1 giorno 50 ore 2 minuti 10 secondi</code>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="🚮 Chiudi", callback_data="close_menu")]
            ])
        )
        return False

    context.chat_data["limit_user_requests"]["duration"] = timedelta_to_seconds(parsed)
    return True


async def handle_request_limitation_topic(update: Update, context: CustomContext):
    data = update.callback_query.data.split("/")[-1]
    sections = get_request_limiting_detail(context=context, what="sections")
    if data in ("block_all", "unblock_all"):
        for platform, categories in sections.items():
            for category in categories:
                sections[platform][category] = (data == "block_all")
        return

    platform_str, category_str = data.split("-")
    sections[platform_str][category_str] = not sections[platform_str][category_str]


def all_sections_are(context: CustomContext, what: bool):
    sections = get_request_limiting_detail(context=context, what="sections")
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
