from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ModerationList
from aimods_bot.src.helpers.constants.path_navigation import ModerationListsRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel


async def render_antispam_links_list_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        list_type: ModerationList
):
    text = _build_text(list_type)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text=f"👁 Visiona {list_type.capitalize()}",
                    callback_key=base_path.add(ModerationListsRoute.VIEW)
                )
            ],
            [
                ButtonItem(text="➕ Aggiungi Elemento", callback_key=base_path.add(ModerationListsRoute.ADD)),
                ButtonItem(text="➖ Rimuovi Elemento", callback_key=base_path.add(ModerationListsRoute.REMOVE))
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


async def render_antispam_edit_link_list_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        text: str
):
    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]]
    )


def _build_text(list_type: ModerationList):
    return (
        "📨 <b>Impostazioni Anti-Spam</b>\n\n"
        f"↦ {list_type.icon} <i>Blocco Link – {list_type.value.capitalize()}</i>\n\n"
        f"▫️ Da qui puoi gestire la {list_type.value.capitalize()} dei link.\n\n"
        f"ℹ {list_type.description}"
    )
