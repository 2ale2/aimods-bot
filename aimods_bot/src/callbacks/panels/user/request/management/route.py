from typing import Literal
from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.callbacks.panels.user.request.management.render import \
    render_user_request_panel, render_user_request_management_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def user_request_management_route(update: Update, context: ContextTypes.DEFAULT_TYPE, path: list[str]):
    if len(path) == 0:
        await render_user_request_management_panel(update=update, context=context)
        return PCS.USER_CONVERSATION

    await user_request_action_route(update=update, context=context, platform=path[0], path=path[1:])


async def user_request_action_route(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        platform: Literal["android", "windows", "ios", "macos"],
        path: list[str]):

    if len(path) == 0:
        await render_user_request_panel(update=update, context=context, platform=platform)
        return PCS.USER_CONVERSATION


