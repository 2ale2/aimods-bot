from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ChatType
from aimods_bot.src.helpers.constants.path_navigation import ModerationListsRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel


async def render_antispam_whitelist_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        send: bool = False
):
    text = _build_whitelist_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [ButtonItem(text="👁 Visiona Whitelist", callback_key=base_path.add(ModerationListsRoute.VIEW))],
            [
                ButtonItem(text="➕ Aggiungi Elemento", callback_key=base_path.add(ModerationListsRoute.ADD)),
                ButtonItem(text="➖ Rimuovi Elemento", callback_key=base_path.add(ModerationListsRoute.REMOVE))
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
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


async def render_antispam_whitelist_view_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _build_whitelist_view_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="👤 Utenti", callback_key=base_path.add(ChatType.USER)),
                ButtonItem(text="👥 Gruppi", callback_key=base_path.add(ChatType.GROUP)),
            ],
            [
                ButtonItem(text="📢 Canali", callback_key=base_path.add(ChatType.CHANNEL)),
                ButtonItem(text="🤖 Bot", callback_key=base_path.add(ChatType.BOT)),
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


def _build_whitelist_view_text() -> str:
    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ 📄 <i>Gestione Whitelist</i>\n\n"
            f"🔹 Scegli la categoria degli ID da visionare.")

    return text
