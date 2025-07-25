from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.allow_after.route import \
    antispam_link_allow_after_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.route import antispam_links_list_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.render import render_antispam_links_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def antispam_links_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_antispam_links_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "punishment":
            # La punizione in base a cosa viene spammato verrà sviluppata in seguito
            await not_implemented_yet(update=update, context=context)
        case "allow_after":
            return await antispam_link_allow_after_route(update=update, context=context, path=path[1:])
        case "whitelist":
            return await antispam_links_list_route(update=update, context=context, l="whitelist", path=path[1:])
        case "blacklist":
            return await antispam_links_list_route(update=update, context=context, l="blacklist", path=path[1:])
        case "greylist":
            return await antispam_links_list_route(update=update, context=context, l="greylist", path=path[1:])

    return PCS.ADMIN_CONVERSATION
