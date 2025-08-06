from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.punishment.handle import set_punishment_type, \
    set_punishment_duration, set_as_parent
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.render import render_punishment_panel, \
    render_punishment_duration_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def punishment_route(update: Update, context: CallbackContext, setting: str, path: list[str]):
    if len(path) == 0:
        await render_punishment_panel(update=update, context=context, setting=setting)
        return PCS.ADMIN_CONVERSATION

    match path[-1]:
        case "duration":
            await render_punishment_duration_panel(update=update, context=context, setting=setting)
            return PCS.SET_PUNISHMENT_DURATION
        case "endless":
            return await set_punishment_duration(update=update, context=context)
        case "antispam" | "antiflood":
            # L'utente ha scelto di impostare la punizione come la macro categoria
            return await set_as_parent(update=update, context=context, setting=setting)

    # L'utente ha premuto un tipo di punizione
    await set_punishment_type(context=context, setting=setting, punishment=path[-1])
    await render_punishment_panel(update=update, context=context, setting=setting)
    return PCS.ADMIN_CONVERSATION
