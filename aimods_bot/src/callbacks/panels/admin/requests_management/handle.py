from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.constants import ChannelMembership
from aimods_bot.src.helpers.constants.path_navigation import AdminRequestManagementRoute
from aimods_bot.src.infra.log import logger
from aimods_bot.src.helpers.models.requests import BaseRequest

log = logger.getChild(__name__)


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
