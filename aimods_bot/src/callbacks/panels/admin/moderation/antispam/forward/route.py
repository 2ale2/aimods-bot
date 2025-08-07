from telegram import Update
from telegram.ext import CallbackContext


async def antispam_forward_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        pass

    match path[0]:
        case "punishment":
            pass
        case "rate_limit":
            pass
