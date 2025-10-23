from telegram import Update

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.models import ButtonItem
from aimods_bot.src.helpers.constants.constants import PUNISHMENT_EMOJIS
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel
from aimods_bot.src.helpers.utils.time_utils import get_duration_text, sec_value_limited


async def render_antispam_panel(update: Update, context: CustomContext):
    text = await _build_text(context=context)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="moderation/security_filters/antispam",
        text=text,
        keyboard=[
            [
                ButtonItem(text="On ☂️", callback_key="toggle_on"),
                ButtonItem(text="Off 🌂", callback_key="toggle_off")
            ],
            [
                ButtonItem(text="⚖️ Punizione", callback_key="punishment"),
                ButtonItem(text="📄 Whitelist", callback_key="whitelist")
            ],
            [
                ButtonItem(text="⛓️‍💥 Blocco Link", callback_key="link"),
                ButtonItem(text="💬 Blocco Menzioni", callback_key="mention")
            ],
            [
                ButtonItem(text="👥 Blocco Inoltro", callback_key="forward"),
                ButtonItem(text="🎞 Blocco Media", callback_key="media")
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


async def _build_text(context: CustomContext):
    antispam_config = get_value(context, "moderation.antispam")

    toggle = antispam_config["toggle"]
    punishment = antispam_config["punishment"]["type"]
    time_total_seconds = antispam_config["punishment"]["time"]

    punishment_limited = sec_value_limited(time_total_seconds)
    time_text = (
        get_duration_text(time_total_seconds) if not punishment_limited
        else "♾️ A Tempo Indeterminato"
    )

    text = (
        "📨 <b>Impostazioni Anti-Spam</b>"
        "\n\n▫️ Qui puoi configurare le <b>difese automatiche</b> contro <b>spammer e bot malevoli</b>. "
        "Attiva solo ciò che serve per evitare falsi positivi.\n\n"
        f"🔸 <u>Stato</u> – {'☂️' if toggle else '🌂'} <i>{'On' if toggle else 'Off'}</i>\n"
        f"🔸 <u>Punizione</u> – {PUNISHMENT_EMOJIS[punishment]} <i>{punishment.capitalize()}</i>\n"
        f"🔸 <u>Tempo</u> – <i>{time_text}</i>\n\n")

    if punishment_limited:
        text += (
            "⚠️ Per regole imposte da Telegram, un tempo inferiore a 30 secondi "
            "o maggiore di 365 giorni equivale a tempo indeterminato.\n\n"
        )

    text += "🔹 Scegli un'opzione."
    return text

