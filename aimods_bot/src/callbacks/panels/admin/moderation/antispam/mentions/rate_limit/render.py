from typing import Literal

from telegram import Update
from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction
from aimods_bot.src.helpers.constants.path_navigation.common import DigitRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem

from aimods_bot.src.helpers.constants.path_navigation.moderation import ModerationSettingRoute, RateLimitTimeRoute
from aimods_bot.src.helpers.utils.time_utils import get_rate_limit_text, pluralize
from aimods_bot.src.helpers.utils.telegram_utils import get_toggle_text, create_and_render_panel


async def render_antispam_mentions_rate_limit_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _build_rate_limit_text(context)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="☂️ On", callback_key=base_path.add(GlobalAction.TOGGLE_ON)),
                ButtonItem(text="🌂️ Off", callback_key=base_path.add(GlobalAction.TOGGLE_OFF)),
            ],
            [
                ButtonItem(text="⏲️ Tempo", callback_key=base_path.add(ModerationSettingRoute.TIME)),
                ButtonItem(text="️📝 Numero Menzioni", callback_key=base_path.add(ModerationSettingRoute.MENTION))
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


def _build_rate_limit_text(context: CustomContext) -> str:
    antispam_mention_rate_limit_config = get_value(context, "moderation.antispam.mention.rate_limit")
    toggle = antispam_mention_rate_limit_config[ModerationSettingRoute.TOGGLE]
    time = antispam_mention_rate_limit_config[ModerationSettingRoute.TIME]
    mentions = antispam_mention_rate_limit_config[ModerationSettingRoute.MENTION]

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
        setting: Literal[ModerationSettingRoute.TIME, ModerationSettingRoute.MENTION],
        base_path: PathBuilder
):
    text = _build_rate_limit_setting_text(context, setting)
    if setting == ModerationSettingRoute.TIME:
        keyboard = [
            [
                ButtonItem(text="5 Secondi", callback_key=base_path.add(RateLimitTimeRoute.SEC_5)),
                ButtonItem(text="10 Secondi", callback_key=base_path.add(RateLimitTimeRoute.SEC_10)),
                ButtonItem(text="30 Secondi", callback_key=base_path.add(RateLimitTimeRoute.SEC_30))
            ],
            [
                ButtonItem(text="1 Minuto", callback_key=base_path.add(RateLimitTimeRoute.MIN_1)),
                ButtonItem(text="2 Minuti", callback_key=base_path.add(RateLimitTimeRoute.MIN_2)),
                ButtonItem(text="3 Minuti", callback_key=base_path.add(RateLimitTimeRoute.MIN_3))
            ],
            [
                ButtonItem(text="5 Minuti", callback_key=base_path.add(RateLimitTimeRoute.MIN_5)),
                ButtonItem(text="7 Minuti", callback_key=base_path.add(RateLimitTimeRoute.MIN_7)),
                ButtonItem(text="10 Minuti", callback_key=base_path.add(RateLimitTimeRoute.MIN_10))
            ],
            [
                ButtonItem(text="20 Minuti", callback_key=base_path.add(RateLimitTimeRoute.MIN_20)),
                ButtonItem(text="1 Ora", callback_key=base_path.add(RateLimitTimeRoute.HOUR_1)),
                ButtonItem(text="12 Ore", callback_key=base_path.add(RateLimitTimeRoute.HOUR_12))
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    else:  # mention
        keyboard = [
            [
                ButtonItem(text="2 Menzioni", callback_key=base_path.add(DigitRoute.TWO)),
                ButtonItem(text="3 Menzioni", callback_key=base_path.add(DigitRoute.THREE)),
                ButtonItem(text="4 Menzioni", callback_key=base_path.add(DigitRoute.FOUR))
            ],
            [
                ButtonItem(text="5 Menzioni", callback_key=base_path.add(DigitRoute.FIVE)),
                ButtonItem(text="6 Menzioni", callback_key=base_path.add(DigitRoute.SIX)),
                ButtonItem(text="7 Menzioni", callback_key=base_path.add(DigitRoute.SEVEN))
            ],
            [
                ButtonItem(text="8 Menzioni", callback_key=base_path.add(DigitRoute.EIGHT)),
                ButtonItem(text="9 Menzioni", callback_key=base_path.add(DigitRoute.NINE)),
                ButtonItem(text="10 Menzioni", callback_key=base_path.add(DigitRoute.TEN))
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


def _build_rate_limit_setting_text(
        context: CustomContext,
        setting: Literal[ModerationSettingRoute.TIME, ModerationSettingRoute.MENTION]
):
    antispam_mention_rate_limit_config = get_value(context, "moderation.antispam.mention.rate_limit")
    value = antispam_mention_rate_limit_config[setting]
    if setting == ModerationSettingRoute.MENTION:
        value_text = f"{pluralize(value, 'Menzione', 'Menzioni')}"
    else:
        value_text = get_rate_limit_text(value)

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ ⏱️ <i>Blocco Menzioni</i> – <i>Rate Limit: {setting.label}</i>\n\n"
            "▫ Imposta il <b>"
            f"{'tempo del Rate Limit' if setting == ModerationSettingRoute.TIME else 'numero di menzioni'}</b>.\n\n"
            f"🔸 <u>{setting.label}</u> – <i>{value_text}</i>\n\n"
            "🔹 Scegli un'opzione.")

    return text
