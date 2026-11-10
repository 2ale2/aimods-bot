import html

from telegram import Update, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.error import BadRequest

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.features.requests.admin.contact.links import (
    LinkFailure, PrivateChatLink, classify_link_error, remember_link_failure, resolve_private_chat_link,
    known_link_failure,
)
from aimods_bot.src.features.requests.models import PLATFORM_CATEGORY_REGISTRY, BaseRequest
from aimods_bot.src.infra.log import logger
from aimods_bot.src.ui.helpers import create_and_render_panel
from aimods_bot.src.ui.panel import ButtonItem, Panel, PanelConfig
from aimods_bot.src.ui.path_navigation import AdminRequestManagementRoute, AdminRoute, GlobalAction, UserRoute, \
    UserManageRequestsRoute, NotificationAction
from aimods_bot.src.ui.routing import PathBuilder

log = logger.getChild(__name__)

_UNKNOWN_FAILURE = "unknown"


def _get_header(subtitle: str) -> str:
    return f"❔ <b>Gestione Richieste</b>\n\n→ 💬 <i>{subtitle}</i>\n\n"


def get_request_label(request: BaseRequest) -> str:
    """Es. «Gioco Windows – Cyberpunk 2077», già in HTML."""
    platform = request.section.platform
    category = request.section.category
    label = f"<b>{PLATFORM_CATEGORY_REGISTRY[platform][category].label} {platform.label}</b>"
    if request.name:
        label += f" – <i>{html.escape(request.name)}</i>"
    return label


# ---------------------------------------------------------------------------
# Sotto-pannello «Contatta Autore»
# ---------------------------------------------------------------------------

async def render_admin_contact_author_panel(
        update: Update,
        context: CustomContext,
        request: BaseRequest,
        base_path: PathBuilder
):
    """
    Mostra il link diretto alla chat dell'autore, quando Telegram lo consente, e sempre
    il tasto per farlo avvisare dal bot.

    Un tasto `tg://user` rifiutato fa fallire tutto il messaggio: per questo il primo
    tentativo è fatto qui, intercettando l'errore, e solo dopo si ridisegna senza tasto.
    """
    link = await resolve_private_chat_link(bot=context.bot, user_id=request.user_id)
    failure: LinkFailure | str | None = known_link_failure(request.user_id) if link is None else None

    if link is not None and not link.via_username and update.callback_query:
        try:
            await _edit_panel_raising(
                update=update,
                text=_get_contact_author_text(request=request, link=link, failure=None),
                keyboard=_get_contact_author_keyboard(base_path=base_path, link=link)
            )
            return
        except BadRequest as e:
            failure = classify_link_error(e)
            if failure is None:
                log.warning(f"Direct link to {request.user_id} rejected for an unexpected reason: {e}")
                failure = _UNKNOWN_FAILURE
            else:
                remember_link_failure(user_id=request.user_id, failure=failure)
            link = None

    await create_and_render_panel(
        update=update,
        context=context,
        text=_get_contact_author_text(request=request, link=link, failure=failure),
        keyboard=_get_contact_author_keyboard(base_path=base_path, link=link)
    )


async def _edit_panel_raising(update: Update, text: str, keyboard: list[list[ButtonItem]]) -> None:
    """Come `Panel.render` in modifica, ma lascia passare il `BadRequest` al chiamante."""
    markup = InlineKeyboardMarkup(Panel(PanelConfig(text=text, keyboard=keyboard)).build_keyboard(
        fallback=str(AdminRoute.ROOT)
    ))
    try:
        await update.effective_message.edit_text(
            text=text,
            reply_markup=markup,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except BadRequest as e:
        if "not modified" in str(e).lower():
            return
        raise


def _get_contact_author_text(
        request: BaseRequest,
        link: PrivateChatLink | None,
        failure: LinkFailure | str | None
) -> str:
    text = (
        f"{_get_header('Contatta Autore')}"
        f"▪️ Richiesta <code>{request.id}</code> ({get_request_label(request)}) "
        f"dell'utente <code>{request.user_id}</code>.\n\n"
    )

    if link is not None:
        if link.via_username:
            text += "▫ L'utente ha uno username pubblico: <b>💬 Apri Chat</b> porta direttamente alla sua chat.\n"
        else:
            text += ("▫ L'utente non ha uno username, ma la sua privacy permette il link diretto: "
                     "<b>💬 Apri Chat</b> porta alla sua chat.\n")
        text += ("<blockquote>ℹ Se l'utente accetta messaggi solo dai contatti (o li fa pagare), "
                 "potresti non riuscire a scrivergli: in quel caso fallo avvisare dal bot.</blockquote>\n")
    else:
        match failure:
            case LinkFailure.PRIVACY:
                text += ("<blockquote>🔒 L'utente non ha uno username e la sua privacy "
                         "(<i>Messaggi inoltrati</i>) non permette il link diretto al suo account.</blockquote>\n")
            case LinkFailure.INVALID:
                text += ("<blockquote>⚠️ Telegram non riconosce l'account dell'utente: potrebbe "
                         "averlo eliminato.</blockquote>\n")
            case _:
                text += "<blockquote>⚠️ Non sono riuscito a creare il link diretto alla chat.</blockquote>\n"

    text += ("\n▫ Con <b>📨 Avvisa l'Autore</b> il bot gli scrive che vorresti contattarlo per questa "
             "richiesta, con un tasto per scriverti.\n\n"
             "🔹 Scegli un'opzione.")
    return text


def _get_contact_author_keyboard(base_path: PathBuilder, link: PrivateChatLink | None) -> list[list[ButtonItem]]:
    keyboard = []
    if link is not None:
        keyboard.append([ButtonItem(text="💬 Apri Chat", url=link.url)])
    keyboard.append([ButtonItem(
        text="📨 Avvisa l'Autore",
        callback_key=base_path.add(AdminRequestManagementRoute.NOTIFY_AUTHOR)
    )])
    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])
    return keyboard


# ---------------------------------------------------------------------------
# Avviso all'autore
# ---------------------------------------------------------------------------

def get_admin_display_name(context: CustomContext, admin_id: int, fallback: str) -> str:
    return context.pydb.admins.get(admin_id) or fallback


def get_author_notice_text(request: BaseRequest, admin_name: str) -> str:
    return (
        "📨 <b>Un Admin Vuole Contattarti</b>\n\n"
        f"▫ <b>{html.escape(admin_name)}</b> vorrebbe chiederti qualche chiarimento sulla tua richiesta "
        f"<code>{request.id}</code> ({get_request_label(request)}).\n\n"
        "🔹 Premi il tasto qui sotto per scrivergli e <b>inoltragli questo messaggio</b>, "
        "così saprà di quale richiesta si tratta."
    )


def get_author_notice_keyboard(request: BaseRequest, admin_name: str, admin_url: str) -> list[list[ButtonItem]]:
    return [
        [ButtonItem(text=f"💬 Scrivi a {admin_name}", url=admin_url)],
        [
            ButtonItem(text="🚮 Chiudi", callback_key=PathBuilder(GlobalAction.CLOSE_MENU)),
            ButtonItem(
                text="👁 Visiona Richiesta",
                callback_key=PathBuilder(
                    UserRoute.ROOT,
                    UserRoute.VIEW_REQUESTS,
                    UserManageRequestsRoute.ACTIVE,
                    str(request.id),
                    NotificationAction.FROM_NOTIFICATION
                )
            )
        ]
    ]


async def render_admin_notify_author_confirmation_panel(
        update: Update,
        context: CustomContext,
        request: BaseRequest,
        base_path: PathBuilder
):
    admin_name = get_admin_display_name(context, update.effective_user.id, update.effective_user.first_name)
    preview = get_author_notice_text(request=request, admin_name=admin_name)
    text = (
        f"{_get_header('Avvisa Autore')}"
        "▪️ Il bot manderà questo messaggio all'autore della richiesta, con un tasto per scriverti:\n\n"
        f"<blockquote>{preview}</blockquote>\n\n"
        "🔹 Confermi l'invio?"
    )
    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=[
            [ButtonItem(text="✅ Invia", callback_key=base_path.add(GlobalAction.YES))],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


def build_user_markup(keyboard: list[list[ButtonItem]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(Panel(PanelConfig(text="", keyboard=keyboard)).build_keyboard(
        fallback=str(UserRoute.ROOT)
    ))
