from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.antiflood.render import render_antiflood_panel
from aimods_bot.src.callbacks.panels.admin.moderation.antiflood.handle import toggle_antiflood
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def antiflood_route(update: Update, context: CustomContext, path: list[str]):
    if len(path) == 0:
        await render_antiflood_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    if "toggle" in path[0]:
        await toggle_antiflood(update=update, context=context)
        await render_antiflood_panel(update=update, context=context)

    match path[0]:
        case "punishment":
            return await punishment_route(update=update, context=context, setting="antiflood", root=path[1:])
        case "message_number":
            await not_implemented_yet(update=update, context=context)
        case "message_time":
            await not_implemented_yet(update=update, context=context)

    return PCS.ADMIN_CONVERSATION
