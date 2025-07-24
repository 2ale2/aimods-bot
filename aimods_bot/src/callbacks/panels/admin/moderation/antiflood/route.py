from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antiflood.render import render_antiflood_panel
from aimods_bot.src.callbacks.panels.admin.moderation.antiflood.handle import toggle_antiflood
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def antiflood_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_antiflood_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    if "toggle" in path[0]:
        await toggle_antiflood(update=update, context=context)
        await render_antiflood_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
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
