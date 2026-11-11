from telegram import Update
from telegram.constants import KeyboardButtonStyle
from telegram.ext import InvalidCallbackData, ConversationHandler

from aimods_bot.src.app.menus.start import start
from aimods_bot.src.features.requests.user.route import user_requests_management_route
from aimods_bot.src.features.settings.user.route import user_settings_management_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.ui.conversation_states import PrivateConversationState
from aimods_bot.src.ui.path_navigation import UserRoute, GlobalAction
from aimods_bot.src.ui.helpers import create_and_render_panel
from aimods_bot.src.ui.panel import ButtonItem
from aimods_bot.src.infra.log import logger
from aimods_bot.src.ui.routing import PathBuilder
from aimods_bot.src.infra.telegram.utils import safe_delete
from aimods_bot.src.features.moderation.members import check_auth

log = logger.getChild(__name__)


@check_auth()
async def user_main_router(update: Update, context: CustomContext):
    if not update.callback_query:
        raise ValueError("No callback query in Update!")

    c_data = update.callback_query.data
    if isinstance(c_data, InvalidCallbackData):
        return await start(update=update, context=context)

    if c_data is None:
        raise ValueError("Callback data must not be None!")

    path = PathBuilder.from_string(c_data)

    # Expected "admin/<path>"
    if path.segments and path.segments[0] == UserRoute.ROOT:
        path = path.pop(0)

    if not len(path):
        return await start(update=update, context=context)

    try:
        match path.segments:
            case [main_route_el, *rest] if main_route_el in (UserRoute.ADD_REQUEST, UserRoute.VIEW_REQUESTS):
                return await user_requests_management_route(
                    update=update,
                    context=context,
                    root=PathBuilder(main_route_el),
                    relative_path=PathBuilder(*rest)
                )
            case [UserRoute.MANAGE_SETTINGS, *rest]:
                return await user_settings_management_route(
                    update=update,
                    context=context,
                    root=PathBuilder(UserRoute.MANAGE_SETTINGS),
                    relative_path=PathBuilder(*rest)
                )
             
            case [UserRoute.SPONSOR]:
                await _render_sponsor_message(
                    update=update, 
                    context=context,
                    base_path=PathBuilder(UserRoute.SPONSOR)
                )
                return PrivateConversationState.USER_CONVERSATION

            case [close_action] if close_action in (GlobalAction.CLOSE_MENU, GlobalAction.CLOSE):
                await safe_delete(update=update, context=context)
                if close_action == GlobalAction.CLOSE_MENU:
                    return ConversationHandler.END
                return PrivateConversationState.USER_CONVERSATION
    finally:
        await update.callback_query.answer()


async def _render_sponsor_message(update: Update, context: CustomContext, base_path: PathBuilder):
    text = ("<tg-emoji emoji-id=\"5424818078833715060\">📣</tg-emoji> <b>Sponsorizza il Tuo Servizio con AiMods™</b>\n\n"
            "<tg-emoji emoji-id=\"5431821053074630770\">❔</tg-emoji> "
            "<i>Hai una community da far crescere o un servizio digitale da promuovere?</i>\n\n"
            "<tg-emoji emoji-id=\"5258203794772085854\">⚡️</tg-emoji> "
            "Fallo davanti a un pubblico 100% in target. La nostra community conta oltre <b>14.000 utenti</b> "
            "appassionati di tecnologia con una media di <b>1.500 visualizzazioni reali in 24h</b>.\n\n"
            "<tg-emoji emoji-id=\"5285221724634239278\">💎</tg-emoji> "
            "<b><i>L'Esclusiva: il Pacchetto Weekend</i></b>\n"
            "<blockquote>Nel fine settimana non pubblichiamo contenuti: "
            "il tuo post sponsorizzato rimarrà <b>l'ultimo messaggio visibile per 24 o 48 ore consecutive</b>, "
            "senza essere \"oscurato\" da altri contenuti. Questo garantisce una <b>visibilità assoluta</b> e un "
            "<b>tasso di click nettamente superiore alla media</b>.</blockquote>\n\n"
            "<tg-emoji emoji-id=\"5231200819986047254\">📊</tg-emoji> <b>Cosa Offriamo</b>\n"
            "    • Slot standard 24h (con 1h fissato in alto)\n"
            "    • Esclusiva Weekend (Sabato e/o Domenica)\n"
            "    • Post Pinnato (fissato in alto)\n\n"
            "<tg-emoji emoji-id=\"5974464899336637626\">💬</tg-emoji> <b>Clicca sul pulsante</b> qui sotto per "
            "<b>contattare l'admin</b>, <b>richiedere il listino prezzi</b> o <b>creare un'offerta su misura</b>. "
            "Senza impegno!")
    
    keyboard = [
        [ButtonItem(text="🎩 Contatta l'Admin", url="https://t.me/prof_layton", style=KeyboardButtonStyle.BLUE)],
        [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
    ]
    
    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=keyboard
    )
    