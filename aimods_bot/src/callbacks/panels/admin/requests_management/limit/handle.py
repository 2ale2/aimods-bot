from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import CATEGORY_DETAILS
from aimods_bot.src.helpers.utils.time_utils import parse_duration, timedelta_to_seconds


def set_user_requests_limiting_item(context: CustomContext):
    """Crea la struttura dati nella persistenza, se non è presente; ritorna la struttura."""
    topics = {}
    for platform, categories in CATEGORY_DETAILS.items():
        topics[platform] = {}
        for category in categories:
            topics[platform][category] = False

    return context.chat_data.setdefault("limit_user_requests", {
        "user_id": 0,
        "duration": 0,
        "topics": topics
    })


def get_limited_user(context: CustomContext):
    limiting_item = set_user_requests_limiting_item(context=context)
    return limiting_item["user_id"]


def get_limited_topics(context: CustomContext):
    limiting_item = set_user_requests_limiting_item(context=context)
    return limiting_item["topics"]


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
                [InlineKeyboardButton(text="🚮 Chiudi", callback_data="close")]
            ])
        )
        return False

    context.chat_data["limit_user_requests"]["duration"] = timedelta_to_seconds(parsed)
    return True


async def handle_request_limitation_topic(update: Update, context: CustomContext):
    data = update.callback_query.data.split("/")[-1]
    topics = get_limited_topics(context=context)
    if data in ("block_all", "unblock_all"):
        for platform, categories in topics.items():
            for category in categories:
                topics[platform][category] = (data == "block_all")
        return

    platform_str, category_str = data.split("-")
    topics[platform_str][category_str] = not topics[platform_str][category_str]


def all_topics_are(context: CustomContext, what: bool):
    topics = get_limited_topics(context=context)
    for platform, categories in topics.items():
        for category in categories:
            if topics[platform][category] != what:
                return False
    return True
