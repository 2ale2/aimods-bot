from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.utils.time_utils import get_allow_after_text


async def render_antispam_links_allow_after_panel(update: Update, context: CallbackContext):
    text = await _build_text(context=context)

    antispam_link_allow_after_panel = Panel(
        PanelConfig(
            base_path="moderation/security_filters/antispam/links/allow_after",
            text=text,
            keyboard=[
                [ButtonItem(text="🆓 Nessun Limite", callback_key="off")],
                [
                    ButtonItem(text="1 Minuto", callback_key="1_min"),
                    ButtonItem(text="2 Minuti", callback_key="2_min"),
                    ButtonItem(text="️3 Minuti", callback_key="3_min")
                ],
                [
                    ButtonItem(text="️5 Minuti", callback_key="5_min"),
                    ButtonItem(text="10 Minuti", callback_key="10_min"),
                    ButtonItem(text="30 Minuti", callback_key="30_min")
                ],
                [
                    ButtonItem(text="1 Ora", callback_key="1_hour"),
                    ButtonItem(text="5 Ore", callback_key="5_hour"),
                    ButtonItem(text="12 Ore", callback_key="12_hour")
                ],
                [
                    ButtonItem(text="1 Giorno", callback_key="1_day"),
                    ButtonItem(text="5 Giorni", callback_key="5_day"),
                    ButtonItem(text="1 Settimana", callback_key="1_week")
                ],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await antispam_link_allow_after_panel.render(update=update, context=context)


async def _build_text(context: CallbackContext):
    antispam_config = get_value(context, "moderation.antispam.link")

    allow_after = antispam_config['allow_after']
    allow_after_text = get_allow_after_text(allow_after)

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ ⌛️ <i>Blocco Link – Consenti Dopo</i>\n\n"
            "▫ Da qui puoi impostare <b>dopo quanto tempo dall'ingresso nel gruppo un utente può mandare un "
            "qualsiasi link, a prescindere che questo debba essere punito o meno</b>.\n\n"
            # La punizione granulare verrà implementata in seguito
            # f"☝️ La punizione comminata sarà quella "
            # f"<b>impostata per lo spamming dei link</b> ({punishment_text}).\n\n"
            f"⌛️ <b>Consenti Dopo</b> – <i>{allow_after_text}</i>\n\n"
            f"🔹 Scegli una durata tra quelle proposte.")

    return text
