from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.render import render_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def moderation_router(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "security_filters":
            pass
        case "user_moderation":
            pass
        case "media_contents":
            pass
        case "community_settings":
            pass


async def security_and_filters_router(update: Update, context: CallbackContext, path: list[str]):
    match path[0]:
        case "antispam_settings":
            pass
        case "antiflood_settings":
            pass
        case "forbidden_words_settings":
            pass
        case "length_settings":
            pass
