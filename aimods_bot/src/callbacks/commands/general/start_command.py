from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS

log = logger.getChild("start_command")


async def get_panel(update: Update, admin: bool):
    fn = update.effective_user.first_name
    if admin:
        return Panel(
            PanelConfig(
                base_path="admin",
                text=("🎛 <b>Pannello di Controllo</b>\n\n"
                      f"▫️ Ciao {fn}! Questo è il pannello di controllo "
                      f"per l'amministrazione del canale e del gruppo.\n\n"
                      "🔹 Scegli un'opzione per cominciare."),
                keyboard=[
                    [
                        ButtonItem(text="♟ Moderazione", callback_key="moderation"),
                        ButtonItem(text="⚙ Impostazioni", callback_key="settings")
                    ],
                    [
                        ButtonItem(text="❔ Gestione Richieste", callback_key="manage_requests"),
                        ButtonItem(text="🔐 Chiudi", callback_key="close_menu")
                    ]
                ],
            ),
            send=True
        )
    else:
        return Panel(
            PanelConfig(
                base_path="user",
                text=("🚪 <b>Pannello Utente</b>\n\n"
                      f"▫️ Ciao {fn}! Questo è il tuo pannello utente. Qui potrai gestire le tue richieste.\n\n"
                      "➕ <u>In futuro tante altre funzionalità</u>.\n\n"
                      "🔹 Scegli un'opzione per cominciare."),
                keyboard=[
                    [
                        ButtonItem(text="♟ Gestisci Richieste", callback_key="manage_requests"),
                        ButtonItem(text="❔ Effettua una Richiesta", callback_key="manage_requests/add_request")
                    ],
                    [ButtonItem(text="🔐 Chiudi", callback_key="close_menu")]
                ]
            ),
            send=True
        )


async def start(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context)

    admin = context.is_user_admin

    panel = await get_panel(update=update, admin=admin)
    await panel.render(update=update, context=context)

    return PCS.ADMIN_CONVERSATION if admin else PCS.USER_CONVERSATION
