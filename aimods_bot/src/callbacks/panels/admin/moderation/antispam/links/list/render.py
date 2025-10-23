from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.models import ButtonItem
from aimods_bot.src.helpers.constants.constants import LIST_DETAILS
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel


async def render_antispam_links_list_panel(update: Update, context: CustomContext, l: str):
    text = _build_text(l)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=update.callback_query.data,
        text=text,
        keyboard=[
            [ButtonItem(text=f"👁 Visiona {l.capitalize()}", callback_key="view")
             ],
            [
                ButtonItem(text="➕ Aggiungi Elemento", callback_key="add"),
                ButtonItem(text="➖ Rimuovi Elemento", callback_key="remove")
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


def _build_text(l: str):
    list_item = LIST_DETAILS[l]

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ {list_item['icon']} <i>Blocco Link – {l.capitalize()}</i>\n\n"
            f"▫️ Da qui puoi gestire la {l.capitalize()} dei link.\n\n"
            f"ℹ {list_item['desc']}"
        )

    return text
