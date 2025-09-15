from telegram import Update

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.utils.time_utils import get_allow_after_text
from aimods_bot.src.helpers.constants.constants import MODERATION_DISPLAY_ITEMS


async def render_allow_after_panel(update: Update, context: CustomContext, setting: str):
    text = await _build_text(context=context, setting=setting)

    allow_after_panel = Panel(
        PanelConfig(
            base_path=f"moderation/security_filters/{setting}/allow_after",
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

    await allow_after_panel.render(update=update, context=context)


async def _build_text(context: CustomContext, setting: str) -> str:
    map_to_word = {
        "link": "link",
        "mention": "menzione"
    }
    setting = setting.split('/')
    antispam_config = get_value(context, f"moderation.{'.'.join(setting)}")

    allow_after = antispam_config['allow_after']
    allow_after_text = get_allow_after_text(allow_after)
    
    setting_item = MODERATION_DISPLAY_ITEMS[setting[0]]
    sub_setting = map_to_word[setting[1]]

    text = (f"{setting_item.display_icon} <b>Impostazioni {setting_item.display_name}</b>\n\n"
            f"↦ ⌛️ <i>Blocco {sub_setting.capitalize()} – Consenti Dopo</i>\n\n"
            "▫ Da qui puoi impostare <b>dopo quanto tempo dall'ingresso nel gruppo un utente può mandare "
            f"qualsiasi {sub_setting} non presente nella relativa Whitelist</b>. Una <b>violazione</b> a tale limite "
            f"comporta il <b>ban immediato</b>, a prescindere dalla punizione impostata per il settaggio "
            f"{setting_item.display_name.lower()}.\n\n"
            # La punizione granulare verrà implementata in seguito
            # f"☝️ La punizione comminata sarà quella "
            # f"<b>impostata per lo spamming dei link</b> ({punishment_text}).\n\n"
            f"⌛️ <b>Consenti Dopo</b> – <i>{allow_after_text}</i>\n\n"
            f"🔹 Scegli una durata tra quelle proposte.")

    return text
