from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.route import antispam_route
from aimods_bot.src.callbacks.panels.admin.moderation.render import render_moderation_panel, \
    render_security_filters_panel
from aimods_bot.src.callbacks.panels.admin.moderation.antiflood.route import antiflood_route
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def moderation_router(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_moderation_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "security_filters":
            return await security_and_filters_router(update=update, context=context, path=path[1:])
        case "user_moderation":
            await not_implemented_yet(update=update, context=context)
        case "media_contents":
            await not_implemented_yet(update=update, context=context)
        case "community_settings":
            await not_implemented_yet(update=update, context=context)


async def security_and_filters_router(update: Update, context: CallbackContext, path: list[str]):
    if len(path):
        match path[0]:
            case "antispam":
                return await antispam_route(update=update, context=context, path=path[1:])
            case "antiflood":
                return await antiflood_route(update=update, context=context, path=path[1:])
            case "forbidden_words":
                await not_implemented_yet(update=update, context=context)
            case "length":
                await not_implemented_yet(update=update, context=context)

    await render_security_filters_panel(update=update, context=context)
    return PCS.ADMIN_CONVERSATION
