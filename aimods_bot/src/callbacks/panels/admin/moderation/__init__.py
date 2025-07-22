from telegram import Update
from telegram.ext import CallbackContext


async def moderation_router(update: Update, context: CallbackContext, callback_data: str):
    s = callback_data.split("/", 1)
    match s[0]:
        case "security_filters":
            pass
        case "user_moderation":
            pass
        case "media_contents":
            pass
        case "community_settings":
            pass


async def security_and_filters_router(update: Update, context: CallbackContext, callback_data: str):
    s = callback_data.split("/", 1)
    match s[0]:
        case "antispam_settings":
            pass
        case "antiflood_settings":
            pass
        case "forbidden_words_settings":
            pass
        case "length_settings":
            pass
