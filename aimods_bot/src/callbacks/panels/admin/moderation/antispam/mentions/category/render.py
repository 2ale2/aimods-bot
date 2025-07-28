from typing import Literal

from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import get_toggle_text


async def render_antispam_mention_category_panel(update: Update, context: CallbackContext, category: str):
    text = _build_text(context=context, category=category)

    antispam_mention_category_panel = Panel(
        PanelConfig(
            base_path=f"moderation/security_filters/antispam/mention/{category}",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="☂️ On", callback_key="on"),
                    ButtonItem(text="🌂 Off", callback_key="off")
                ],
                [ButtonItem(text="📄 Whitelist", callback_key="whitelist")],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await antispam_mention_category_panel.render(update=update, context=context)


def _build_text(context: CallbackContext, category: str) -> str:
    map_to_word = {
        "user": "Utenti",
        "group": "Gruppi",
        "channel": "Canali",
        "bot": "Bot"
    }
    word = map_to_word[category]
    toggle = get_value(context=context, path=f"moderation.antispam.mention.{category}")
    toggle_text = get_toggle_text(toggle)

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ 💬 <i>Blocco Menzioni</i> – <i>Menzioni {word}</i>\n\n"
            f"▫️ Da qui puoi gestire la Whitelist della categoria {word.lower()}, che conterrà "
            f"gli elementi che <b>non verranno considerati in fase di controllo</b>. "
            f"Puoi anche disattivare completamente il controllo sull'intera categoria.\n\n"
            f"🔸 <u>Toggle</u> – {toggle_text}\n\n"
            f"🔹 Scegli un'opzione.")

    return text


async def render_antispam_mention_category_whitelist_panel(
        update: Update,
        context: CallbackContext,
        category: Literal["user", "group", "channel", "bot"]
):
    text = _build_whitelist_text(category=category)

    antispam_mention_category_whitelist_panel = Panel(
        PanelConfig(
            base_path=f"moderation/security_filters/antispam/mention/{category}/whitelist",
            text=text,
            keyboard=[
                [ButtonItem(text=f"👁 Visiona Whitelist", callback_key="view")],
                [
                    ButtonItem(text="➕ Aggiungi Elemento", callback_key="add"),
                    ButtonItem(text="➖ Rimuovi Elemento", callback_key="remove")
                ],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await antispam_mention_category_whitelist_panel.render(update=update, context=context)


def _build_whitelist_text(category: str) -> str:
    map_to_word = {
        "user": "Utenti",
        "group": "Gruppi",
        "channel": "Canali",
        "bot": "Bot"
    }
    word = map_to_word[category]
    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ 💬 <i>Blocco Menzioni</i> – <i>Whitelist Menzione {word}</i>\n\n"
            f"▫️ Da qui puoi gestire la lista di identificativi che non verranno controllati.\n\n"
            f"🔹 Scegli un'opzione.")

    return text
