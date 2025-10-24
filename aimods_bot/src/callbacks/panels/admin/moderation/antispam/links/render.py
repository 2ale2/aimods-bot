from telegram import Update

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.models import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel
from aimods_bot.src.helpers.utils.time_utils import get_allow_after_text


async def render_antispam_links_panel(update: Update, context: CustomContext):
    text = await _build_text(context=context)

    await create_and_render_panel(
        update=update,
        context=context,
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


async def _build_text(context: CustomContext):
    antispam_config = get_value(context, "moderation.antispam.link")

    allow_after = antispam_config['allow_after']
    allow_after_text = get_allow_after_text(allow_after)

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ ⛓️‍💥 <i>Blocco Link</i>\n\n"
            "▫️ Da qui puoi impostare le regole di gestione dei link.\n\n"
            f"🔸 <u>Consenti Link Dopo</u>: <i>{allow_after_text}</i>\n\n"
            f"🔹 Scegli un'opzione.")

    return text
