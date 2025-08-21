from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.user.request_management.request.windows.handle import (
    RequestDataManager)
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("windows_request")


async def request_name(update: Update, context: CallbackContext) -> int:
    """Richiede il nome del software o dell'app."""
    context.chat_data["bot_message_id"] = update.effective_message.id

    await RequestDataManager.request_detail(
        update=update,
        context=context,
        detail="name"
    )

    return RCS.REQUEST_NAME


async def request_link(update: Update, context: CallbackContext) -> int:
    """Richiede il nome del software o dell'app."""

    await RequestDataManager.request_detail(
        update=update,
        context=context,
        detail="link"
    )

    return RCS.REQUEST_LINK


async def request_version(update: Update, context: CallbackContext) -> int:
    """Richiede il nome del software o dell'app."""

    await RequestDataManager.request_detail(
        update=update,
        context=context,
        detail="version"
    )

    return RCS.REQUEST_VERSION


async def request_functionalities(update: Update, context: CallbackContext) -> int:
    """Richiede il nome del software o dell'app."""

    await RequestDataManager.request_detail(
        update=update,
        context=context,
        detail="functionalities"
    )

    return RCS.REQUEST_FUNCTIONALITIES


async def request_steamtools(update: Update, context: CallbackContext) -> int:
    """Richiede il nome del software o dell'app."""

    await RequestDataManager.request_detail(
        update=update,
        context=context,
        detail="steamtools"
    )

    return RCS.REQUEST_STEAMTOOLS
