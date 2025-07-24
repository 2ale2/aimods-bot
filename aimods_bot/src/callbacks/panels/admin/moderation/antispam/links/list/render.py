from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.helpers.constants.constants import PanelConfig, Panel, ButtonItem

list_detail = {
        "whitelist": {
            "icon": "📨",
            "desc": "I domini aggiunti a questa lista <b>non verranno puniti</b> se spammati."
        },
        "blacklist": {
            "icon": "📓",
            "desc": "I domini aggiunti a questa lista verranno <b>puniti con il ban, "
                    "indipendentemente dalla punizione impostata</b>."
        },
        "greylist": {
            "icon": "🧙‍♂️",
            "desc": "I link aggiunti a questa lista <b>non verranno puniti</b>."
        }
    }


async def render_antispam_links_list_panel(update: Update, context: CallbackContext, l: str):
    text = _build_text(l)

    antispam_links_list_panel = Panel(
        PanelConfig(
            base_path=update.callback_query.data,
            text=text,
            keyboard=[
                [ButtonItem(text=f"👁 Visiona {l.capitalize()}", callback_key=f"view_{l}")
                ],
                [
                    ButtonItem(text="➕ Aggiungi Elemento", callback_key=f"add_{l}"),
                    ButtonItem(text="➖ Rimuovi Elemento",  callback_key=f"remove_{l}")
                ],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await antispam_links_list_panel.render(update=update, context=context)


def _build_text(l: str):
    list_item = list_detail[l]

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ {list_item['icon']} <i>Blocco Link – {l.capitalize()}</i>\n\n"
            f"▫️ Da qui puoi gestire la {l.capitalize()} dei link.\n\n"
            f"ℹ {list_item['desc']}"
        )

    return text
