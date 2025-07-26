from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.utils.time_utils import get_allow_after_text


async def render_antispam_links_panel(update: Update, context: CallbackContext):
    text = await _build_text(context=context)

    antispam_panel = Panel(
        PanelConfig(
            base_path="moderation/security_filters/antispam/link",
            text=text,
            keyboard=[
                [ButtonItem(text="⚖️ Punizione", callback_key="punishment")],
                [ButtonItem(text="⌛️ Consenti Dopo", callback_key="allow_after")],
                [
                    ButtonItem(text="📄 Whitelist", callback_key="whitelist"),
                    ButtonItem(text="📓 Blacklist", callback_key="blacklist")
                ],
                [ButtonItem(text="🧙‍♂️ Greylist", callback_key="greylist")],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await antispam_panel.render(update=update, context=context)


async def _build_text(context: CallbackContext):
    antispam_config = get_value(context, "moderation.antispam.link")

    allow_after = antispam_config['allow_after']
    allow_after_text = get_allow_after_text(allow_after)

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ ⛓️‍💥 <i>Blocco Link</i>\n\n"
            "▫️ Da qui puoi impostare le regole di gestione dei link.\n\n"
            f"🔸 <u>Consenti Link Dopo</u>: <i>{allow_after_text}</i>\n\n"
            f"🔹 Scegli un'opzione.")

    return text
