from telegram import Update

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction, SecurityFiltersRoute, AntifloodRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.constants.constants import PUNISHMENT_EMOJIS
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel
from aimods_bot.src.helpers.utils.time_utils import get_duration_text, sec_value_limited


async def render_antiflood_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = await _build_text(context=context)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="On ☂️", callback_key=base_path.add(GlobalAction.TOGGLE_ON)),
                ButtonItem(text="Off 🌂", callback_key=base_path.add(GlobalAction.TOGGLE_OFF))
            ],
            [ButtonItem(text="⚖️ Punizione", callback_key=base_path.add(SecurityFiltersRoute.PUNISHMENT))],
            [ButtonItem(text="💬 Numero Messaggi", callback_key=base_path.add(AntifloodRoute.MESSAGE_NUMBER))],
            [ButtonItem(text="🕔 Tempo Messaggi", callback_key=base_path.add(AntifloodRoute.MESSAGE_TIME))],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


async def _build_text(context: CustomContext):
    antiflood_config = get_value(context, "moderation.antiflood")

    toggle = antiflood_config["toggle"]
    punishment = antiflood_config["punishment"]["type"]
    time_total_seconds = antiflood_config["punishment"]["time"]
    number_messages = antiflood_config["settings"]["number_messages"]
    time_messages = antiflood_config["settings"]["time_messages"]

    punishment_limited = sec_value_limited(time_total_seconds)
    time_text = (
        get_duration_text(time_total_seconds) if not punishment_limited
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
