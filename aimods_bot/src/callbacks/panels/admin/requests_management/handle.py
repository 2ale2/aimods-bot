from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.render import render_admin_confirm_rejection_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import MissingParameterException
from aimods_bot.src.core.pydantic import Request
from aimods_bot.src.helpers.constants.constants import RequestStatus, REQUEST_REJECTION_REASONS
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete


async def handle_request_rejection_reason(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context)

    reason = update.message.text

    request = context.pydc.ephimeral.rejecting
    context.pydc.ephimeral.rejecting = None

    if request is None:
        raise MissingParameterException("Missing 'request' parameter inside ChatData.")

    assert isinstance(request, Request)

    await render_admin_confirm_rejection_panel(
        update=update,
        context=context,
        request=request,
        ix=request.id,
        reason=reason
    )

    return PCS.ADMIN_CONVERSATION


async def confirm_rejection(context: CustomContext, ix: int, reason: str):
    if reason in REQUEST_REJECTION_REASONS:
        reason = REQUEST_REJECTION_REASONS[reason]
    await context.edit_request_status(ix=ix, status=RequestStatus.REJECTED, rejection_reason=reason)
