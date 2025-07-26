from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.handle import toggle_antispam
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.route import antispam_links_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.render import render_antispam_panel
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def antispam_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_antispam_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    if "toggle" in path[0]:
        await toggle_antispam(update=update, context=context)
        await render_antispam_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "punishment":
            return await punishment_route(update=update, context=context, setting="antispam", path=path[1:])
        case "links":
            return await antispam_links_route(update=update, context=context, path=path[1:])
        case "mentions":
            await not_implemented_yet(update=update, context=context)
        case "forward":
            await not_implemented_yet(update=update, context=context)
        case "media":
            await not_implemented_yet(update=update, context=context)

    return PCS.ADMIN_CONVERSATION
