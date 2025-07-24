from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.punishment.handle import set_punishment_type
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

    await set_punishment_type(context=context, setting=setting, punishment=path[-1])
    await render_punishment_panel(update=update, context=context, setting=setting)
    return PCS.ADMIN_CONVERSATION