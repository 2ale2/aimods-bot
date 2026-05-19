from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.route import antispam_route
from aimods_bot.src.callbacks.panels.admin.moderation.render import render_moderation_panel, \
    render_security_filters_panel
from aimods_bot.src.callbacks.panels.admin.moderation.antiflood.route import antiflood_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_paths.navigation import ModerationRoute, SecurityFiltersRoute
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def moderation_router(update: Update, context: CustomContext, root: PathBuilder, relative_path: PathBuilder):
    match relative_path.segments:
        case []:
            await render_moderation_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION

        case [ModerationRoute.SECURITY_FILTERS, *rest]:
            return await security_and_filters_router(update=update, context=context, root=root[1:])

    match root[0]:
        case "security_filters":
            return await security_and_filters_router(update=update, context=context, root=root[1:])
        case "user_moderation":
            await not_implemented_yet(update=update, context=context)
        case "media_contents":
            await not_implemented_yet(update=update, context=context)
        case "community_settings":
            await not_implemented_yet(update=update, context=context)


async def security_and_filters_router(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_security_filters_panel(update=update, context=context, base_path=root)
        case [SecurityFiltersRoute.ANTISPAM, *rest]:
            return await antispam_route(update=update, context=context, root=root[1:])
        case [SecurityFiltersRoute.ANTIFLOOD, *rest]:
            return await antiflood_route(update=update, context=context, path=root[1:])
        case [SecurityFiltersRoute.FORBIDDEN_WORDS, *rest]:
            await not_implemented_yet(update=update, context=context)
        case [SecurityFiltersRoute.LENGHT]:
            await not_implemented_yet(update=update, context=context)

    return PCS.ADMIN_CONVERSATION
