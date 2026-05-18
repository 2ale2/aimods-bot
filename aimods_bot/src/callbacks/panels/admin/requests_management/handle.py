from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.render import render_admin_confirm_rejection_panel, \
    send_user_request_status_changed_notification
from aimods_bot.src.callbacks.panels.user.request.management.render import render_user_request_archive_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import MissingParameterException
from aimods_bot.src.core.pydantic import Request
from aimods_bot.src.helpers.constants.constants import RequestStatus, REQUEST_REJECTION_REASONS
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, username_to_id, wrong_input_message


async def handle_request_rejection_reason(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context)

    reason = update.message.text

    request = context.pydc.ephemeral.working_request

    if request is None:
        raise MissingParameterException("Missing 'request' parameter inside ChatData.")

    assert isinstance(request, Request)
    context.pydc.ephemeral.working_request = None

    await render_admin_confirm_rejection_panel(
        update=update,
        context=context,
        request=request,
        ix=request.id,
        reason=reason
    )

    return PCS.ADMIN_CONVERSATION


async def confirm_rejection(context: CustomContext, ix: int, reason: str):
    final_reason = REQUEST_REJECTION_REASONS.get(reason, reason)

    await context.edit_request_status(
        ix=ix,
        status=RequestStatus.REJECTED,
        rejection_reason=final_reason
    )


async def handle_user_archive_identifier(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context)

    raw_input = update.message.text.strip()

    if raw_input.isdigit():
        target_user_id = int(raw_input)
    else:
        target_user_id = await username_to_id(username=raw_input)

    if target_user_id is None:
        await wrong_input_message(
            update=update,
            context=context,
            correct_message="Invia un ID numerico o uno @username valido."
        )
        return PCS.SET_USER_FOR_REQUEST_ARCHIVE

    if target_user_id in context.pydb.admins:
        await wrong_input_message(
            update=update,
            context=context,
            correct_message="Invia uno <b>username</b> o un <b>ID numerico</b> che <b>non appartengano</b> agli admin."
        )
        return PCS.SET_USER_FOR_REQUEST_ARCHIVE

    await render_user_request_archive_panel(
        update=update,
        context=context,
        user_id=target_user_id,
        requested_by_admin=True
    )
    return PCS.ADMIN_CONVERSATION
