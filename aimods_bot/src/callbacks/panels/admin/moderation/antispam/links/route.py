from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.allow_after.route import antispam_link_allow_after_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.route import antispam_links_list_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.render import render_antispam_links_panel
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import SecurityFiltersRoute
from aimods_bot.src.helpers.models.routing import PathBuilder


async def antispam_link_route(update: Update, context: CustomContext, root: PathBuilder, relative_path: PathBuilder):
    match relative_path.segments:
        case []:
            await render_antispam_links_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION

        case [SecurityFiltersRoute.PUNISHMENT, *rest]:
            root.add(SecurityFiltersRoute.PUNISHMENT)
            return await punishment_route(
                update=update,
                context=context,
                setting="antispam/link",
                root=root,
                relative_path=PathBuilder(*rest)
            )

        case [SecurityFiltersRoute.ALLOW_AFTER, *rest]:
            root.add(SecurityFiltersRoute.ALLOW_AFTER)
            match PathBuilder(*rest).segments:
                case []:
                    return await antispam_link_allow_after_route(
                        update=update,
                        context=context,
                        setting="antispam/link",
                        relative_path=PathBuilder(*rest)
                    )

    match root[0]:
        case "allow_after":
            if len(root) == 1:
                return await antispam_link_allow_after_route(
                    update=update,
                    context=context,
                    setting="antispam/link",
                    relative_path=root[1:]
                )
            await antispam_link_allow_after_route(
                update=update,
                context=context,
                setting="antispam/link",
                relative_path=root[1:]
            )
            await render_antispam_links_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION
        case "whitelist":
            return await antispam_links_list_route(update=update, context=context, l="whitelist", path=root[1:])
        case "blacklist":
            return await antispam_links_list_route(update=update, context=context, l="blacklist", path=root[1:])
        case "greylist":
            return await antispam_links_list_route(update=update, context=context, l="greylist", path=root[1:])

    return PCS.ADMIN_CONVERSATION
