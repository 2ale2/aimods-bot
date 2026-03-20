from telegram import Update

from aimods_bot.src.helpers.constants.conversation_paths.navigation import GlobalAction, AdminRoute, ModerationRoute

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.models import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel


async def render_moderation_panel(update: Update, context: CustomContext):
    await create_and_render_panel(
        update=update,
        context=context,
        base_path=AdminRoute.MODERATION,
        text=("♟ <b>Impostazioni – Moderazione Gruppo e Canale</b>\n\n"
              "▫️ Da questo menù puoi regolare le impostazioni di moderazione del gruppo e del canale di "
              "<i>AIMods</i>.\n\n🔹 Scegli un'opzione."),
        keyboard=[
            [ButtonItem(text="🔐 Sicurezza e Filtri", callback_key=ModerationRoute.SECURITY_FILTERS)],
            [ButtonItem(text="⚠️ Moderazione Utenti", callback_key=ModerationRoute.USER_MODERATION)],
            [ButtonItem(text="🎞 Messaggi e Contenuti", callback_key=ModerationRoute.MEDIA_CONTENT)],
            [ButtonItem(text="👥 Gestione Community", callback_key=ModerationRoute.COMMUNITY)],
            [ButtonItem(text="🏠 Home", callback_key=GlobalAction.MAIN_MENU)]
        ]
    )


async def render_security_filters_panel(update: Update, context: CustomContext):
    await create_and_render_panel(
        update=update,
        context=context,
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
