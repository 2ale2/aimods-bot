from telegram import Update, LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, TelegramError

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.features.requests.admin.contact.links import (
    LinkFailure, classify_link_error, resolve_private_chat_link,
)
from aimods_bot.src.features.requests.admin.contact.render import (
    build_user_markup, get_admin_display_name, get_author_notice_keyboard, get_author_notice_text,
)
from aimods_bot.src.features.requests.models import BaseRequest
from aimods_bot.src.infra.log import logger

log = logger.getChild(__name__)

# Gli alert accettano al massimo 200 caratteri.
_ADMIN_LINK_RESTRICTED = (
    "🔒 Non hai uno username e la tua privacy (Messaggi inoltrati) blocca il link al tuo account: "
    "l'utente non saprebbe come scriverti. Imposta uno username o cambia la privacy e riprova."
)


async def notify_author(update: Update, context: CustomContext, request: BaseRequest) -> bool:
    """
    Manda all'autore l'avviso che un admin vuole contattarlo, con un tasto verso la chat
    dell'admin. L'esito arriva all'admin come alert. Ritorna True se l'avviso è partito.
    """
    query = update.callback_query
    admin = update.effective_user
    admin_name = get_admin_display_name(context, admin.id, admin.first_name)

    # Niente cache per l'admin: se ha appena cambiato la privacy, deve poter riprovare subito.
    admin_link = await resolve_private_chat_link(bot=context.bot, user_id=admin.id, use_cache=False)

    try:
        await context.bot.send_message(
            chat_id=request.user_id,
            text=get_author_notice_text(request=request, admin_name=admin_name),
            reply_markup=build_user_markup(get_author_notice_keyboard(
                request=request, admin_name=admin_name, admin_url=admin_link.url
            )),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except Forbidden as e:
        log.info(f"Cannot notify author {request.user_id} of request {request.id}: {e}")
        await query.answer("🚫 L'utente ha bloccato il bot o ha eliminato l'account: non posso avvisarlo.",
                           show_alert=True)
        return False
    except BadRequest as e:
        failure = classify_link_error(e)
        if failure is not None and not admin_link.via_username:
            # L'unico tasto `tg://user` del messaggio è quello verso l'admin.
            log.info(f"Admin {admin.id} link rejected ({failure}) while notifying {request.user_id}")
            await query.answer(_ADMIN_LINK_RESTRICTED if failure == LinkFailure.PRIVACY else
                               "⚠️ Telegram non accetta il link al tuo account. Imposta uno username e riprova.",
                               show_alert=True)
        else:
            log.warning(f"Cannot notify author {request.user_id} of request {request.id}: {e}")
            await query.answer("❌ Non sono riuscito a inviare l'avviso all'utente.", show_alert=True)
        return False
    except TelegramError as e:
        log.warning(f"Cannot notify author {request.user_id} of request {request.id}: {e}")
        await query.answer("❌ Non sono riuscito a inviare l'avviso all'utente. Riprova.", show_alert=True)
        return False

    await query.answer("✅ Avviso inviato all'autore della richiesta.", show_alert=True)
    return True
