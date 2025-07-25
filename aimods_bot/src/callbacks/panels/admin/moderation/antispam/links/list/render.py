from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.helpers.constants.constants import PanelConfig, Panel, ButtonItem
from aimods_bot.src.helpers.constants.constants import LIST_DETAILS


async def render_antispam_links_list_panel(update: Update, context: CallbackContext, l: str):
    text = _build_text(l)

    antispam_links_list_panel = Panel(
        PanelConfig(
            base_path=update.callback_query.data,
            text=text,
            keyboard=[
                [ButtonItem(text=f"👁 Visiona {l.capitalize()}", callback_key="view")
                ],
                [
                    ButtonItem(text="➕ Aggiungi Elemento", callback_key="add"),
                    ButtonItem(text="➖ Rimuovi Elemento",  callback_key="remove")
                ],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await antispam_links_list_panel.render(update=update, context=context)


def _build_text(l: str):
    list_item = LIST_DETAILS[l]

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ {list_item['icon']} <i>Blocco Link – {l.capitalize()}</i>\n\n"
            f"▫️ Da qui puoi gestire la {l.capitalize()} dei link.\n\n"
            f"ℹ {list_item['desc']}"
        )

    return text
