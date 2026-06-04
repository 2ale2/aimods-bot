from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.antiflood.render import render_antiflood_panel
from aimods_bot.src.callbacks.panels.admin.moderation.antiflood.handle import toggle_antiflood
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction, SecurityFiltersRoute, AntifloodRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def antiflood_route(update: Update, context: CustomContext, root: PathBuilder, relative_path: PathBuilder):
    match relative_path.segments:
        case []:
            await render_antiflood_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION

        case [toggle] if toggle in (GlobalAction.TOGGLE_ON, GlobalAction.TOGGLE_OFF):
            await toggle_antiflood(update=update, context=context)
            await render_antiflood_panel(update=update, context=context)

        case [SecurityFiltersRoute.PUNISHMENT, *rest]:
            root.add(SecurityFiltersRoute.PUNISHMENT)
            return await punishment_route(
                update=update,
                context=context,
                setting="antiflood",
                root=root,
                relative_path=PathBuilder(*rest)
            )

        case [AntifloodRoute.MESSAGE_NUMBER]:
            await not_implemented_yet(update=update, context=context)

        case [AntifloodRoute.MESSAGE_TIME]:
            await not_implemented_yet(update=update, context=context)

    return PCS.ADMIN_CONVERSATION
