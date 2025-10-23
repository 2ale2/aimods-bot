from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.models import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel


async def render_antispam_whitelist_panel(
        update: Update,
        context: CustomContext,
        send: bool = False
):
    text = _build_whitelist_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="moderation/security_filters/antispam/whitelist",
        text=text,
        keyboard=[
            [ButtonItem(text="👁 Visiona Whitelist", callback_key="view")],
            [
                ButtonItem(text="➕ Aggiungi Elemento", callback_key="add"),
                ButtonItem(text="➖ Rimuovi Elemento", callback_key="remove")
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ],
        send=send
    )


def _build_whitelist_text() -> str:
    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ 📄 <i>Gestione Whitelist</i>\n\n"
            "▫️ Da qui puoi gestire la Whitelist dell'Anti-Spam.\n\n"
            "ℹ Gli elementi inseriti in questa Whitelist non saranno soggetti ad alcun controllo da parte "
            "dell'Anti-Spam.\n\n"
            "🔹 Scegli un'opzione.")

    return text


async def render_antispam_whitelist_view_panel(update: Update, context: CustomContext):
    text = _build_whitelist_view_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="moderation/security_filters/antispam/whitelist/view",
        text=text,
        keyboard=[
            [
                ButtonItem(text="👤 Utenti", callback_key="user"),
                ButtonItem(text="👥 Gruppi", callback_key="group"),
            ],
            [
                ButtonItem(text="📢 Canali", callback_key="channel"),
                ButtonItem(text="🤖 Bot", callback_key="bot")
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


def _build_whitelist_view_text() -> str:
    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ 📄 <i>Gestione Whitelist</i>\n\n"
            f"🔹 Scegli la categoria degli ID da visionare.")

    return text
