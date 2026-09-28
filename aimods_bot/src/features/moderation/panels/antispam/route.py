from telegram import Update

from aimods_bot.src.features.moderation.panels.antispam.forward.route import antispam_forward_route
from aimods_bot.src.features.moderation.panels.antispam.handle import toggle_antispam
from aimods_bot.src.features.moderation.panels.antispam.links.route import antispam_link_route
from aimods_bot.src.features.moderation.panels.antispam.mentions.route import antispam_mention_route
from aimods_bot.src.features.moderation.panels.antispam.render import render_antispam_panel
from aimods_bot.src.features.moderation.panels.antispam.whitelist.route import antispam_whitelist_route
from aimods_bot.src.features.moderation.panels.punishment.route import punishment_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.ui.path_navigation import GlobalAction, SecurityFiltersRoute, \
    AntispamRoute
from aimods_bot.src.ui.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.infra.log import logger
from aimods_bot.src.ui.routing import PathBuilder
from aimods_bot.src.ui.helpers import not_implemented_yet


log = logger.getChild(__name__)


async def antispam_route(update: Update, context: CustomContext, root: PathBuilder, relative_path: PathBuilder):
    match relative_path.segments:
        case []:
            await render_antispam_panel(update=update, context=context, base_path=root)

        case [toggle] if toggle in (GlobalAction.TOGGLE_ON, GlobalAction.TOGGLE_OFF):
            await toggle_antispam(update=update, context=context)
            await render_antispam_panel(update=update, context=context, base_path=root)

        case [SecurityFiltersRoute.PUNISHMENT, *rest]:
            root = root.add(SecurityFiltersRoute.PUNISHMENT)
            return await punishment_route(
                update=update,
                context=context,
                setting=SecurityFiltersRoute.ANTISPAM,
                root=root,
                relative_path=PathBuilder(*rest)
            )

        case [SecurityFiltersRoute.WHITELIST, *rest]:
            return await antispam_whitelist_route(
                update=update,
                context=context,
                root=root.add(SecurityFiltersRoute.WHITELIST),
                relative_path=PathBuilder(*rest)
            )
        case [AntispamRoute.LINK, *rest]:
            return await antispam_link_route(
                update=update,
                context=context,
                root=root.add(AntispamRoute.LINK),
                relative_path=PathBuilder(*rest)
            )
        case [AntispamRoute.MENTION, *rest]:
            return await antispam_mention_route(
                update=update,
                context=context,
                root=root.add(AntispamRoute.MENTION),
                relative_path=PathBuilder(*rest)
            )
        case [AntispamRoute.FORWARD, *rest]:
            return await antispam_forward_route(
                update=update,
                context=context,
                root=root.add(AntispamRoute.FORWARD),
                relative_path=PathBuilder(*rest)
            )
        case [AntispamRoute.MEDIA]:
            await not_implemented_yet(update=update, context=context)
        case _:
            log.warning(f"Unhandled path in admin_requests_management: {relative_path.build()}")

    return PCS.ADMIN_CONVERSATION
