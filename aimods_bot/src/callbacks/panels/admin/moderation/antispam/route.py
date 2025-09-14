from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.forward.route import antispam_forward_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.handle import toggle_antispam
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.route import antispam_link_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.route import antispam_mention_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.render import render_antispam_panel
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.route import antispam_whitelist_route
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def antispam_route(update: Update, context: CustomContext, path: list[str]):
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
        case "whitelist":
            return await antispam_whitelist_route(update=update, context=context, path=path[1:])
        case "link":
            return await antispam_link_route(update=update, context=context, path=path[1:])
        case "mention":
            return await antispam_mention_route(update=update, context=context, path=path[1:])
        case "forward":
            return await antispam_forward_route(update=update, context=context, path=path[1:])
        case "media":
            await not_implemented_yet(update=update, context=context)

    return PCS.ADMIN_CONVERSATION
