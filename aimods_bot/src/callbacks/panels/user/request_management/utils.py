from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.user.request_management.route import user_request_route
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS


async def route_back_to_main(update: Update, context: CallbackContext):
    """Gestisce il ritorno al menu principale"""
    await user_request_route(update=update, context=context, path=[])
    return RCS.MAIN_BACKER
