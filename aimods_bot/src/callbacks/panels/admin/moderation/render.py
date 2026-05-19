from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_paths.navigation import ModerationRoute, SecurityFiltersRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel


async def render_moderation_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=("♟ <b>Impostazioni – Moderazione Gruppo e Canale</b>\n\n"
              "▫️ Da questo menù puoi regolare le impostazioni di moderazione del gruppo e del canale di "
              "<i>AIMods</i>.\n\n🔹 Scegli un'opzione."),
        keyboard=[
            [ButtonItem(text="🔐 Sicurezza e Filtri", callback_key=ModerationRoute.SECURITY_FILTERS)],
            [ButtonItem(text="⚠️ Moderazione Utenti", callback_key=ModerationRoute.USER_MODERATION)],
            [ButtonItem(text="🎞 Messaggi e Contenuti", callback_key=ModerationRoute.MEDIA_CONTENT)],
            [ButtonItem(text="👥 Gestione Community", callback_key=ModerationRoute.COMMUNITY)],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


async def render_security_filters_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text="<b>🔐 Sicurezza e Filtri</b>\n\n🔹 Scegli un'opzione.",
        keyboard=[
            [ButtonItem(text="📨 Anti-Spam", callback_key=SecurityFiltersRoute.ANTISPAM)],
            [ButtonItem(text="🌊 Anti-Flood", callback_key=SecurityFiltersRoute.ANTIFLOOD)],
            [ButtonItem(text="🖊 Parole Bandite", callback_key=SecurityFiltersRoute.FORBIDDEN_WORDS)],
            [ButtonItem(text="👁‍🗨 Controlli", callback_key=SecurityFiltersRoute.CHECKS)],
            [ButtonItem(text="🔞 Contenuti Inappropriati", callback_key=SecurityFiltersRoute.INAPPROPRIATE_CONTENT)],
            [ButtonItem(text="📏 Lunghezza Messaggi", callback_key=SecurityFiltersRoute.LENGHT)],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )
