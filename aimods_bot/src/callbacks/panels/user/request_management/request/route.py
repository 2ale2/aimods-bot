from typing import Optional
from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.user.request_management.request.render import render_user_cant_request_panel, \
    render_user_request_main_panel
from aimods_bot.src.callbacks.panels.user.request_management.request.handle import can_user_request
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def user_request_route(update: Update, context: CallbackContext, path=Optional[list[str]]):
    if path is not None and len(path) == 0:
        answer = await can_user_request(update=update, context=context)
        if answer.yn:
            await render_user_request_main_panel(update=update, context=context)
            return PCS.NEW_REQUEST
        else:
            await render_user_cant_request_panel(update=update, context=context, reason=answer.reason)
            return PCS.USER_CONVERSATION
