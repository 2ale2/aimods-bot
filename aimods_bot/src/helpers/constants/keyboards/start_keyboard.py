from telegram import InlineKeyboardButton
from aimods_bot.src.helpers.constants.constants import PanelDict


admin_keyboard_panel = PanelDict(
    text="🎛 <b>Pannello di Controllo</b>\n\n"
         "▫️ Questo è il pannello di controllo per l'amministrazione del canale e del gruppo.\n\n"
         "🔹 Scegli un'opzione per cominciare.",
    keyboard=[
        [
            InlineKeyboardButton(text="♟ Moderazione", callback_data="moderation"),
            InlineKeyboardButton(text="⚙ Impostazioni", callback_data="settings")
        ],
        [
            InlineKeyboardButton(text="❔ Gestione Richieste", callback_data="requests"),
            InlineKeyboardButton(text="🔐 Chiudi", callback_data="close_menu")
        ]
    ]
)

user_keyboard_panel = PanelDict(
    text="🎛 <b>Benvenuto Utente</b>\n\n"
         "▫️ Questo è il bot ufficiale di <i>AiMods</i>.\n\n"
         "🔹 Scegli un'opzione per cominciare.",
    keyboard=[
        [InlineKeyboardButton(text="❔ Effettua una Richiesta", callback_data="requests")]
    ]
)