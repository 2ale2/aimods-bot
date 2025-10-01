from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.allow_after.route import antispam_link_allow_after_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.route import antispam_links_list_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.render import render_antispam_links_panel
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def antispam_link_route(update: Update, context: CustomContext, path: list[str]):
    if len(path) == 0:
        await render_antispam_links_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "punishment":
            return await punishment_route(update=update, context=context, setting="antispam/link", path=path[1:])
        case "allow_after":
            if len(path) == 1:
                return await antispam_link_allow_after_route(
                    update=update,
                    context=context,
                    setting="antispam/link",
                    path=path[1:]
                )
            await antispam_link_allow_after_route(
                update=update,
                context=context,
                setting="antispam/link",
                path=path[1:]
            )
            await render_antispam_links_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION
        case "whitelist":
            return await antispam_links_list_route(update=update, context=context, l="whitelist", path=path[1:])
        case "blacklist":
            return await antispam_links_list_route(update=update, context=context, l="blacklist", path=path[1:])
        case "greylist":
            return await antispam_links_list_route(update=update, context=context, l="greylist", path=path[1:])

    return PCS.ADMIN_CONVERSATION
