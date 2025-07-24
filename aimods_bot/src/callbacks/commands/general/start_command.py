from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.utils.user_utils import is_admin
from aimods_bot.src.helpers.constants.constants import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS

log = logger.getChild("start_command")


admin_panel = Panel(
    PanelConfig(
        base_path="",
        text=("🎛 <b>Pannello di Controllo</b>\n\n"
             "▫️ Questo è il pannello di controllo per l'amministrazione del canale e del gruppo.\n\n"
             "🔹 Scegli un'opzione per cominciare."),
        keyboard=[
            [
                ButtonItem(text="♟ Moderazione", callback_key="moderation"),
                ButtonItem(text="⚙ Impostazioni", callback_key="settings")
            ],
            [
                ButtonItem(text="❔ Gestione Richieste", callback_key="requests"),
                ButtonItem(text="🔐 Chiudi", callback_key="close_menu")
            ]
        ],
    ),
    send=True
)

user_panel = Panel(
    PanelConfig(
        base_path="",
        text=("🎛 <b>Pannello di Controllo</b>\n\n"
             "▫️ Questo è il pannello di controllo per l'amministrazione del canale e del gruppo.\n\n"
             "🔹 Scegli un'opzione per cominciare."),
        keyboard=[
            [
                ButtonItem(text="❔ Effettua una Richiesta", callback_key="requests")
            ]
        ]
    ),
    send=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Due funzioni: la prima per gestire il menu per non staff, l'altra per lo staff
    user_id = update.effective_user.id
    await safe_delete(update=update, context=context)

    if await is_admin(user_id=user_id, context=context):
        await _render_admin_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION
    else:
        await _render_user_panel(update=update, context=context)
        return PCS.USER_CONVERSATION


async def _render_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await admin_panel.render(update=update, context=context)


async def _render_user_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await user_panel.render(update=update, context=context)
