from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.forward.render import render_antispam_forward_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def antispam_forward_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_antispam_forward_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "punishment":
            pass
        case "rate_limit":
            pass
        case "user":
            pass
        case "group":
            pass
        case "channel":
            pass
        case "bot":
            pass


async def antispam_forward_category_route(update: Update, context: CallbackContext, category: str, path: list[str]):
    if len(path) == 0:
        pass
