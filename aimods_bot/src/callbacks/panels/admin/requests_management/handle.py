from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.route import admin_manage_request_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import RequestStatus, RejectRequestReason
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import AdminRequestManagementRoute
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder

log = logger.getChild(__name__)


async def handle_request_rejection_reason(update: Update, context: CustomContext):
    rejection_session = context.pydc.ephemeral.active_rejection_session
    if rejection_session is None:
        raise ValueError("No active request rejection session.")

    if update.callback_query:
        reason_str = update.callback_query.data
        if reason_str not in RejectRequestReason:
            await update.callback_query.answer(text="⚠️ Scegli una motivazione valida o scrivine una.", show_alert=True)
            log.warning(f"Invalid rejection reason from callback query: {reason_str}")
            return PCS.SET_REQUEST_REJECTION_REASON
    elif update.message:
        reason_str = update.message.text
    else:
        raise ValueError("Rejection reason not specified.")

    root_path = PathBuilder.from_string(context.pydc.persistent.root_path)
    relative_path = PathBuilder.from_string(context.pydc.persistent.relative_path)

    if reason_str in RejectRequestReason:
        rejection_session.reason = RejectRequestReason(reason_str).label
    else:
        rejection_session.reason = reason_str

    return await admin_manage_request_route(
        update=update,
        context=context,
        root=root_path,
        relative_path=relative_path.add(AdminRequestManagementRoute.REJECT_REASON_SET),
        ix=rejection_session.request_id
    )


async def confirm_rejection(context: CustomContext, ix: int, reason: str):
    await context.edit_request_status(
        ix=ix,
        status=RequestStatus.REJECTED,
        rejection_reason=reason
    )
    context.pydc.ephemeral.active_rejection_session = None
