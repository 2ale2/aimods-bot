from telegram import Update
from telegram.ext import CallbackContext


async def antispam_router(update: Update, context: CallbackContext, callback_data: str):
    s = callback_data.split("/", 1)
    match s[0]:
        case "toggle_on":
            pass
        case "toggle_off":
            pass
        case "set_punishment":
            pass
        case "set_links":
            pass
        case "set_mentions":
            pass
        case "set_forward":
            pass
        case "set_media":
            pass
