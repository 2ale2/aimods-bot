from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.allow_after.route import antispam_link_allow_after_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.route import antispam_links_list_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.render import render_antispam_links_panel
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ModerationList
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import SecurityFiltersRoute
from aimods_bot.src.helpers.models.routing import PathBuilder


async def antispam_link_route(update: Update, context: CustomContext, root: PathBuilder, relative_path: PathBuilder):
    match relative_path.segments:
        case []:
            await render_antispam_links_panel(update=update, context=context, base_path=root)
            return PCS.ADMIN_CONVERSATION

        case [SecurityFiltersRoute.PUNISHMENT, *rest]:
            return await punishment_route(
                update=update,
                context=context,
                setting="antispam/link",
                root=root.add(SecurityFiltersRoute.PUNISHMENT),
                relative_path=PathBuilder(*rest)
            )

        case [SecurityFiltersRoute.ALLOW_AFTER, *rest]:
            rest_path = PathBuilder(*rest)

            route_result = await antispam_link_allow_after_route(
                update=update,
                context=context,
                setting="antispam/link",
                root=root.add(SecurityFiltersRoute.ALLOW_AFTER),
                relative_path=rest_path
            )

            if not rest_path.segments:
                return route_result

            await render_antispam_links_panel(
                update=update,
                context=context,
                base_path=root + rest_path
            )
            return PCS.ADMIN_CONVERSATION

        case [list_type, *rest] if list_type in ModerationList:
            return await antispam_links_list_route(
                update=update,
                context=context,
                list_type=list_type,
                root=root.add(list_type),
                relative_path=PathBuilder(*rest)
            )

    return PCS.ADMIN_CONVERSATION
