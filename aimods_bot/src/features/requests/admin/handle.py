from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError, BadRequest, Forbidden

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.constants import ChannelMembership
from aimods_bot.src.features.requests.admin.render import get_dm_user_text, get_admin_contact_request_text_and_keyboard
from aimods_bot.src.ui.helpers import create_and_render_panel
from aimods_bot.src.ui.panel import ButtonItem
from aimods_bot.src.ui.path_navigation import AdminRequestManagementRoute
from aimods_bot.src.infra.log import logger
from aimods_bot.src.features.requests.models import BaseRequest
from aimods_bot.src.ui.routing import PathBuilder

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


async def handle_admin_contact_request_sending(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        request: BaseRequest
):
    unable_to_notify_text = "<blockquote>❌ Non è stato possibile notificare l'utente perché {}</blockquote>"
    unable_to_notify_keyboard = [
        [ButtonItem(text="✉️ Riprova", callback_key=base_path)],
        [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
    ]

    if update.effective_user.username is None:
        text = (
            get_dm_user_text(user_id=request.user_id) +
            unable_to_notify_text.format("non hai uno username. Impostalo e riprova.")
        )
        await create_and_render_panel(
            update=update,
            context=context,
            text=text,
            keyboard=unable_to_notify_keyboard
        )
        return

    identifier = None
    try:
        chat_full_info = await context.bot.get_chat(chat_id=request.user_id)
        if chat_full_info and chat_full_info.username:
            identifier = chat_full_info.username
    except TelegramError:
        pass
    except BadRequest as e:
        log.warning(f"Error in API request 'get_chat': {e}")

    if not identifier:
        identifier = request.user_id

    text, reply_markup = get_admin_contact_request_text_and_keyboard(update=update, request=request)
    try:
        await context.bot.send_message(
            chat_id=identifier,
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

        request.admin_dm_request_sent = True

        await create_and_render_panel(
            update=update,
            context=context,
            text="✅ <b>Notifica Inviata</b>\n\n"
                 "<blockquote>ℹ️ L'utente ha la facoltà di ignorare o disattivare le richieste "
                 "di contatto.</blockquote>",
            keyboard=[[ButtonItem(text="🔙 Torna alla richiesta.", callback_key=base_path.back(2))]]
        )
    except Forbidden:
        text = (
                get_dm_user_text(user_id=request.user_id) +
                unable_to_notify_text.format("l'utente ha bloccato il bot.")
        )
        await create_and_render_panel(
            update=update,
            context=context,
            text=text,
            keyboard=unable_to_notify_keyboard
        )
    except Exception as e:
        log.error(f"Unable to send message to user {identifier}: {e}")
        text = (
                get_dm_user_text(user_id=request.user_id) +
                unable_to_notify_text.format("errore dell'API.")
        )
        await create_and_render_panel(
            update=update,
            context=context,
            text=text,
            keyboard=unable_to_notify_keyboard
        )
