from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.constants.constants import PUNISHMENT_EMOJIS
from aimods_bot.src.helpers.utils.time_utils import get_duration_text, sec_value_limited


async def render_antiflood_panel(update: Update, context: CallbackContext):
    text = await _build_text(context=context)

    antiflood_panel = Panel(
        PanelConfig(
            base_path="moderation/security_filters/antiflood",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="On ☂️", callback_key="toggle_on"),
                    ButtonItem(text="Off 🌂", callback_key="toggle_off")
                ],
                [ButtonItem(text="⚖️ Punizione", callback_key="punishment")],
                [ButtonItem(text="💬 Numero Messaggi", callback_key="message_number")],
                [ButtonItem(text="🕔 Tempo Messaggi", callback_key="message_time")],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await antiflood_panel.render(update=update, context=context)


async def _build_text(context: CallbackContext):
    antiflood_config = get_value(context, "moderation.antiflood")

    toggle = antiflood_config["toggle"]
    punishment = antiflood_config["punishment"]["type"]
    time_total_seconds = antiflood_config["punishment"]["time"]
    number_messages = antiflood_config["settings"]["number_messages"]
    time_messages = antiflood_config["settings"]["time_messages"]

    punishment_limited = sec_value_limited(time_total_seconds)
    time_text = (
        await get_duration_text(time_total_seconds) if not punishment_limited
        else "♾️ A Tempo Indeterminato"
    )

    text = (
        "🌊 <b>Impostazioni Anti-Flood</b>\n\n"
        "▫️ Qui puoi configurare le <b>difese automatiche</b> contro <b>il flooding</b>.\n\n"
        f"🔸 <u>Stato</u> – {'☂️' if toggle else '🌂'} <i>{toggle}</i>\n"
        f"🔸 <u>Limite Messaggi</u> – <i>{number_messages}</i>\n"
        f"🔸 <u>Limite di Tempo</u> – <i>{time_messages}</i> secondi\n"
        f"🔸 <u>Punizione</u> – {PUNISHMENT_EMOJIS[punishment]} <i>{punishment.capitalize()}</i>\n"
        f"🔸 <u>Tempo della Punizione</u> – <i>{time_text}</i>\n\n"
    )

    if punishment_limited:
        text += (
            "⚠️ Per regole imposte da Telegram, un tempo inferiore a 30 secondi "
            "o maggiore di 365 giorni equivale a tempo indeterminato.\n\n"
        )

    text += "🔹 Scegli un'opzione."
    return text

