from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.constants.constants import CATEGORY_DETAILS
from aimods_bot.src.helpers.utils.time_utils import parse_duration, timedelta_to_seconds


def new_user_requests_limiting_item(context: ContextTypes.DEFAULT_TYPE):
    topics = {}
    for platform, categories in CATEGORY_DETAILS.items():
        topics[platform] = {}
        for category in categories:
            topics[platform][category] = False

    context.chat_data.setdefault("limit_user_requests", {
        "user_id": 0,
        "duration": 0,
        "topics": topics
    })


async def handle_request_limitation_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
