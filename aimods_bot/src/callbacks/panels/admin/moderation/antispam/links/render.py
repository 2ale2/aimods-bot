from telegram import Update

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ModerationList
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel
from aimods_bot.src.helpers.utils.time_utils import get_allow_after_text
from aimods_bot.src.helpers.constants.path_navigation import SecurityFiltersRoute


async def render_antispam_links_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = await _build_text(context=context)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [ButtonItem(text="⚖️ Punizione", callback_key=base_path.add(SecurityFiltersRoute.PUNISHMENT))],
            [ButtonItem(text="⌛️ Consenti Dopo", callback_key=base_path.add(SecurityFiltersRoute.ALLOW_AFTER))],
            [
                ButtonItem(text="📄 Whitelist", callback_key=base_path.add(ModerationList.WHITELIST)),
                ButtonItem(text="📓 Blacklist", callback_key=base_path.add(ModerationList.BLACKLIST))
            ],
            [ButtonItem(text="🧙‍♂️ Greylist", callback_key=base_path.add(ModerationList.GREYLIST))],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
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


async def render_empty_list_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        list_type: ModerationList
):
    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ {list_type.icon} <i>Blocco Link – {list_type.value.capitalize()}</i>\n\n"
            f"0️⃣ <b>La {list_type.value.capitalize()} è attualmente vuota</b>.")

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]]
    )
