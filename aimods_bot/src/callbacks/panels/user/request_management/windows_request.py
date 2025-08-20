from typing import Literal

from telegram import Update
from telegram.ext import CallbackContext, ContextTypes, ConversationHandler

from aimods_bot.src.callbacks.panels.user.request_management.request.windows.handle import (
    InputHandler, MessageBuilder, KeyboardBuilder, RequestDataManager, handle_back_to_main)
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import edit_message_safely

log = logger.getChild("windows_request")


async def request_name(update: Update, context: CallbackContext) -> int:
    """Richiede il nome del software o dell'app."""
    context.chat_data["bot_message_id"] = update.effective_message.id

    await RequestDataManager.request_detail(
        update=update,
        context=context,
        detail="name",
        back_data="back_category"
    )

    return RCS.REQUEST_NAME
