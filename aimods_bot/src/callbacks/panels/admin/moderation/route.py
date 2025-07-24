from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.render import render_moderation_panel, \
    render_security_filters_panel
from aimods_bot.src.callbacks.panels.admin.moderation.antiflood.route import antiflood_route
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def moderation_router(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_moderation_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "security_filters":
            await render_security_filters_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION
        case "user_moderation":
            pass
        case "media_contents":
            pass
        case "community_settings":
            pass


async def security_and_filters_router(update: Update, context: CallbackContext, path: list[str]):
    match path[0]:
        case "antispam":
            await antiflood_route(update=update, context=context, path=path[1:])
            pass
        case "antiflood":
            pass
        case "forbidden_words":
            pass
        case "length":
            pass

    return PCS.ADMIN_CONVERSATION