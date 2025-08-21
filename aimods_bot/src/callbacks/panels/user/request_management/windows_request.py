from typing import Optional
from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.user.request_management.request.windows.handle import (
    RequestDataManager, RequestField, RequestData)
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.constants.constants import REQUEST_FLOWS
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("request")

RETURN_CONVERSATION_STATES = {
    "name": RCS.REQUEST_NAME,
    "link": RCS.REQUEST_LINK,
    "version": RCS.REQUEST_VERSION,
    "functionalities": RCS.REQUEST_FUNCTIONALITIES,
    "steamtools": RCS.REQUEST_STEAMTOOLS
}


async def request_detail(update: Update, context: CallbackContext) -> int:
    """Richiede il nome del software o dell'app."""
    request_data = RequestDataManager.get_request_data(context)
    requesting = request_data.requesting
    detail = requesting.value

    if "bot_message_id" not in context.chat_data:
        context.chat_data["bot_message_id"] = update.effective_message.id

    await RequestDataManager.request_detail(
        update=update,
        context=context,
        detail=detail
    )

    next_detail = prepare_next_detail(request_data=request_data)
    RequestDataManager.update_field(context=context, field="requesting", value=next_detail)

    return RETURN_CONVERSATION_STATES[detail]


def prepare_next_detail(request_data: RequestData) -> Optional[RequestField]:
    platform = request_data.get_platform()
    category = request_data.get_category()
    requesting = request_data.requesting

    flow = REQUEST_FLOWS[platform.value][category.value]
    ix = flow.index(requesting.value)
    if len(flow) >= ix + 1:
        return RequestField(flow[ix + 1])
    return None
