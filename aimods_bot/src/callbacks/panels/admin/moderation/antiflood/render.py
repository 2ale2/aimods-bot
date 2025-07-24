from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.helpers.constants.constants import Panel, PanelConfig, PUNISHMENT_EMOJIS, ButtonItem
from aimods_bot.src.helpers.utils.time_utils import get_time_text, sec_value_defined


async def render_antiflood_panel(update: Update, context: CallbackContext):
    text = _build_text(context=context)

    antiflood_panel = Panel(
        PanelConfig(
            base_path="moderation/security_filters/antiflood",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="On ☂️", callback_key="toggle_on"),
                    ButtonItem(text="Off 🌂", callback_key="toggle_off")
                ],
                [ButtonItem(text="⚖️ Punizione", callback_key="set_punishment")],
                [ButtonItem(text="⛓️‍💥 Blocco Link", callback_key="set_links")],
                [ButtonItem(text="💬 Blocco Menzioni", callback_key="set_links")],
                [ButtonItem(text="👥 Blocco Inoltro", callback_key="set_forward")],
                [ButtonItem(text="🎞 Blocco Media", callback_key="set_media")],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await antiflood_panel.render(update=update, context=context)


def _build_text(context: CallbackContext):
    antiflood_config = get_value(context, "moderation.antiflood")

    toggle = antiflood_config["toggle"]
    punishment = antiflood_config["punishment"]["type"]
    time_total_seconds = antiflood_config["punishment"]["time"]
    number_messages = antiflood_config["settings"]["number_messages"]
    time_messages = antiflood_config["settings"]["time_messages"]

    punishment_limited = sec_value_defined(time_total_seconds)
    time_text = (
        get_time_text(time_total_seconds) if punishment_limited
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
            "⚠️ <b>Per regole imposte da Telegram, un tempo inferiore a 30 secondi "
            "o maggiore di 365 giorni equivale a tempo indeterminato</b>.\n\n"
        )

    text += "🔹 Scegli un'opzione."
    return text

