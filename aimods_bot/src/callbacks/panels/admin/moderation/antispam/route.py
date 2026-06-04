from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.forward.route import antispam_forward_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.handle import toggle_antispam
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.route import antispam_link_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.route import antispam_mention_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.render import render_antispam_panel
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.route import antispam_whitelist_route
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction, SecurityFiltersRoute, \
    AntispamRoute
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


log = logger.getChild(__name__)


async def antispam_route(update: Update, context: CustomContext, root: PathBuilder, relative_path: PathBuilder):
    match relative_path.segments:
        case []:
            await render_antispam_panel(update=update, context=context)

        case [toggle] if toggle in (GlobalAction.TOGGLE_ON, GlobalAction.TOGGLE_OFF):
            await toggle_antispam(update=update, context=context)
            await render_antispam_panel(update=update, context=context)

        case [SecurityFiltersRoute.PUNISHMENT, *rest]:
            root.add(SecurityFiltersRoute.PUNISHMENT)
            return await punishment_route(
                update=update,
                context=context,
                setting=SecurityFiltersRoute.ANTISPAM,
                root=root,
                relative_path=PathBuilder(*rest)
            )

        case [SecurityFiltersRoute.WHITELIST, *rest]:
            root.add(SecurityFiltersRoute.WHITELIST)
            return await antispam_whitelist_route(
                update=update,
                context=context,
                root=root,
                relative_path=PathBuilder(*rest)
            )
        case [AntispamRoute.LINK, *rest]:
            root.add(AntispamRoute.LINK)
            return await antispam_link_route(
                update=update,
                context=context,
                root=root,
                relative_path=PathBuilder(*rest)
            )
        case [AntispamRoute.MENTION, *rest]:
            root.add(AntispamRoute.MENTION)
            return await antispam_mention_route(
                update=update,
                context=context,
                root=root,
                relative_path=PathBuilder(*rest)
            )
        case [AntispamRoute.FORWARD, *rest]:
            root.add(AntispamRoute.FORWARD)
            return await antispam_forward_route(
                update=update,
                context=context,
                root=root,
                relative_path=PathBuilder(*rest)
            )
        case [AntispamRoute.MEDIA]:
            await not_implemented_yet(update=update, context=context)
        case _:
            log.warning(f"Unhandled path in admin_requests_management: {relative_path.build()}")

    return PCS.ADMIN_CONVERSATION
