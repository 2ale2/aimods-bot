from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.route import admin_manage_request_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import RejectRequestReason, ChannelMembership
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import AdminRequestManagementRoute
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.requests import BaseRequest
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete

log = logger.getChild(__name__)


async def handle_request_rejection_reason(update: Update, context: CustomContext):
    rejection_session = context.pydc.ephemeral.active_rejection_session
    if rejection_session is None:
        raise ValueError("No active request rejection session.")

    root_path = PathBuilder.from_string(context.pydc.persistent.root_path)
    relative_path = PathBuilder.from_string(context.pydc.persistent.relative_path)

    if update.callback_query:
        reason_str = update.callback_query.data
        if reason_str == AdminRequestManagementRoute.REJECT_REASON_BACK:
            return await admin_manage_request_route(
                update=update,
                context=context,
                root=root_path,
                relative_path=relative_path.back(),
                ix=rejection_session.request_id
            )
        if reason_str not in RejectRequestReason:
            await update.callback_query.answer(text="⚠️ Scegli una motivazione valida o scrivine una.", show_alert=True)
            log.warning(f"Invalid rejection reason from callback query: {reason_str}")
            return PCS.SET_REQUEST_REJECTION_REASON
    elif update.message:
        reason_str = update.message.text
        await safe_delete(update=update, context=context)
    else:
        raise ValueError("Rejection reason not specified.")

    if reason_str in RejectRequestReason:
        rejection_session.reason = RejectRequestReason(reason_str).label
    else:
        rejection_session.reason = reason_str

    context.pydc.persistent.root_path = None
    context.pydc.persistent.relative_path = None

    return await admin_manage_request_route(
        update=update,
        context=context,
        root=root_path,
        relative_path=relative_path.add(AdminRequestManagementRoute.REJECT_REASON_SET),
        ix=rejection_session.request_id
    )


async def handle_membership_op(
        update: Update,
        context: CustomContext,
        request: BaseRequest,
        op: AdminRequestManagementRoute
) -> None:
    """
    Riverifica o conferma a mano l'iscrizione dell'autore. L'esito arriva all'admin
    come alert; il pannello lo ridisegna il chiamante.
    """
    query = update.callback_query

    if not request.channel_membership.is_unconfirmed:
        await query.answer("ℹ L'iscrizione di questo utente è già stata gestita.", show_alert=True)
        return

    if op == AdminRequestManagementRoute.CONFIRM_MEMBERSHIP:
        saved = await context.set_request_channel_membership(
            ix=request.id,
            membership=ChannelMembership.MANUALLY_CONFIRMED,
            confirmed_by=update.effective_user.id
        )
        await query.answer(
            "☑️ Iscrizione confermata manualmente." if saved else "❌ Errore nel salvataggio. Riprova.",
            show_alert=not saved
        )
        return

    result = await context.check_channel_membership(user_id=request.user_id)
    if result == ChannelMembership.UNVERIFIED:
        await query.answer("⚠️ Non riesco ancora a verificare l'iscrizione. Controlla che il bot sia "
                           "amministratore del canale, oppure conferma manualmente.", show_alert=True)
        return

    if not await context.set_request_channel_membership(ix=request.id, membership=result):
        await query.answer("❌ Errore nel salvataggio. Riprova.", show_alert=True)
        return

    if result == ChannelMembership.MEMBER:
        await query.answer("✅ L'utente risulta iscritto al canale.", show_alert=True)
    else:
        await query.answer("🚫 L'utente non risulta iscritto al canale.", show_alert=True)
