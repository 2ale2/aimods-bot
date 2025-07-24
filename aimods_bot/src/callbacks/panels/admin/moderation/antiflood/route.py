from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antiflood.render import render_antiflood_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def antiflood_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_antiflood_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION
