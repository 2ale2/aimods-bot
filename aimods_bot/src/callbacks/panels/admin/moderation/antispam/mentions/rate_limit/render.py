from typing import Literal

from telegram import Update
from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.models import ButtonItem
from aimods_bot.src.helpers.utils.time_utils import get_rate_limit_text, pluralize
from aimods_bot.src.helpers.utils.telegram_utils import get_toggle_text, create_and_render_panel


async def render_antispam_mentions_rate_limit_panel(update: Update, context: CustomContext):
    text = _build_rate_limit_text(context)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="moderation/security_filters/antispam/mention/rate_limit",
        text=text,
        keyboard=[
            [
                ButtonItem(text="☂️ On", callback_key="on"),
                ButtonItem(text="🌂️ Off", callback_key="off")
            ],
            [
                ButtonItem(text="⏲️ Tempo", callback_key="time"),
                ButtonItem(text="️📝 Numero Menzioni", callback_key="mention")
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


def _build_rate_limit_text(context: CustomContext) -> str:
    antispam_mention_rate_limit_config = get_value(context, "moderation.antispam.mention.rate_limit")
    toggle = antispam_mention_rate_limit_config["toggle"]
    time = antispam_mention_rate_limit_config["time"]
    mentions = antispam_mention_rate_limit_config["mention"]

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ ⏱️ <i>Blocco Menzioni</i> – <i>Rate Limit</i>\n\n"
            "▫️ Da qui puoi impostare <b>quante menzioni possono essere inviate da uno stesso utente in un arco di "
            "tempo arbitrario</b>. Una <b>violazione</b> a tale limite comporta il <b>ban immediato</b>, "
            "a prescindere dalla punizione impostata per l'anti-spam. Le menzioni presenti in Whitelist "
            "non vengono conteggiate.\n\n"
            f"🔸 <u>Toggle</u> – {get_toggle_text(toggle)}\n"
            f"🔸 <u>Rate-Limit</u> – <i>{pluralize(mentions, 'Menzione', 'Menzioni')} in "
            f"{get_rate_limit_text(time)}</i>\n\n"
            f"🔹 Scegli un'opzione.")

    return text


async def render_antispam_mentions_rate_limit_setting_panel(
        update: Update,
        context: CustomContext,
        setting: Literal['time', 'mention']
):
    text = _build_rate_limit_setting_text(context, setting)
    if setting == 'time':
        keyboard = [
            [
                ButtonItem(text="5 Secondi", callback_key="5"),
                ButtonItem(text="10 Secondi", callback_key="10"),
                ButtonItem(text="30 Secondi", callback_key="30")
            ],
            [
                ButtonItem(text="1 Minuto", callback_key="60"),
                ButtonItem(text="2 Minuti", callback_key="120"),
                ButtonItem(text="3 Minuti", callback_key="180")
            ],
            [
                ButtonItem(text="5 Minuti", callback_key="300"),
                ButtonItem(text="7 Minuti", callback_key="420"),
                ButtonItem(text="10 Minuti", callback_key="600")
            ],
            [
                ButtonItem(text="20 Minuti", callback_key="1200"),
                ButtonItem(text="1 Ora", callback_key="3600"),
                ButtonItem(text="12 Ore", callback_key="43200")
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    else:  # mention
        keyboard = [
            [
                ButtonItem(text="2 Menzioni", callback_key="2"),
                ButtonItem(text="3 Menzioni", callback_key="3"),
                ButtonItem(text="4 Menzioni", callback_key="4")
            ],
            [
                ButtonItem(text="5 Menzioni", callback_key="5"),
                ButtonItem(text="6 Menzioni", callback_key="6"),
                ButtonItem(text="7 Menzioni", callback_key="7")
            ],
            [
                ButtonItem(text="8 Menzioni", callback_key="8"),
                ButtonItem(text="9 Menzioni", callback_key="9"),
                ButtonItem(text="10 Menzioni", callback_key="10")
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"moderation/security_filters/antispam/mention/rate_limit/{setting}",
        text=text,
        keyboard=keyboard
    )


def _build_rate_limit_setting_text(context: CustomContext, setting: Literal['time', 'mention']):
    antispam_mention_rate_limit_config = get_value(context, "moderation.antispam.mention.rate_limit")
    value = antispam_mention_rate_limit_config[setting]
    if setting == "mention":
        value_text = f"{pluralize(value, 'Menzione', 'Menzioni')}"
    else:
        value_text = get_rate_limit_text(value)

    map_to_word = {
        "time": "Tempo",
        "mention": "Numero Menzioni"
    }
    word = map_to_word[setting]

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ ⏱️ <i>Blocco Menzioni</i> – <i>Rate Limit: {word}</i>\n\n"
            F"▫ Imposta il <b>{'tempo del Rate Limit' if setting == 'time' else 'numero di menzioni'}</b>.\n\n"
            f"🔸 <u>{word}</u> – <i>{value_text}</i>\n\n"
            "🔹 Scegli un'opzione.")

    return text
