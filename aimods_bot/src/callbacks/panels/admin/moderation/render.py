from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem

moderation_panel = Panel(
    PanelConfig(
        base_path="moderation",
        text=("♟ <b>Impostazioni – Moderazione Gruppo e Canale</b>\n\n"
              "▫️ Da questo menù puoi regolare le impostazioni di moderazione del gruppo e del canale di "
              "<i>AIMods</i>.\n\n🔹 Scegli un'opzione."),
        keyboard=[
            [ButtonItem(text="🔐 Sicurezza e Filtri", callback_key="security_filters")],
            [ButtonItem(text="⚠️ Moderazione Utenti", callback_key="user_moderation")],
            [ButtonItem(text="🎞 Messaggi e Contenuti", callback_key="media_contents")],
            [ButtonItem(text="👥 Gestione Community", callback_key="community")],
            [ButtonItem(text="🏠 Home", callback_key="main_menu")]
        ]
    )
)

security_filters_panel = Panel(
    PanelConfig(
        base_path="moderation/security_filters",
        text="<b>🔐 Sicurezza e Filtri</b>\n\n🔹 Scegli un'opzione.",
        keyboard=[
            [ButtonItem(text="📨 Anti-Spam", callback_key="antispam")],
            [ButtonItem(text="🌊 Anti-Flood", callback_key="antiflood")],
            [ButtonItem(text="🖊 Parole Bandite", callback_key="forbidden_words")],
            [ButtonItem(text="👁‍🗨 Controlli", callback_key="checks")],
            [ButtonItem(text="🔞 Contenuti Inappropriati", callback_key="inappropriate_content")],
            [ButtonItem(text="📏 Lunghezza Messaggi", callback_key="length")],
            [ButtonItem(text="🔙 Indietro", callback_key="moderation")]
        ]
    )
)


async def render_moderation_panel(update: Update, context: CustomContext):
    await moderation_panel.render(update, context)


async def render_security_filters_panel(update: Update, context: CustomContext):
    await security_filters_panel.render(update, context)

