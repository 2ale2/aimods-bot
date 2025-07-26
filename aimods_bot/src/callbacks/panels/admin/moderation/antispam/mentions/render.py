from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.utils.time_utils import get_allow_after_text, get_rate_limit_text, pluralize


async def render_antispam_mention_panel(update: Update, context: CallbackContext):
    text = await _build_text(context)

    antispam_mention_panel = Panel(
        PanelConfig(
            base_path="moderation/security_filters/antispam/mention",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="⌛️ Consenti Dopo", callback_key="allow_after"),
                    ButtonItem(text="⏱️ Rate Limit", callback_key="rate_limit")
                ],
                [
                    ButtonItem(text="👤 Utenti", callback_key="user"),
                    ButtonItem(text="👥 Gruppi", callback_key="group"),
                ],
                [
                    ButtonItem(text="📢 Canali", callback_key="channel"),
                    ButtonItem(text="🤖 Bot", callback_key="bot")
                ],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await antispam_mention_panel.render(update=update, context=context)


async def _build_text(context: CallbackContext) -> str:
    antispam_mention_config = get_value(context, "moderation.antispam.mention")
    allow_after = antispam_mention_config['allow_after']
    allow_after_text = get_allow_after_text(allow_after)
    rate_limit = antispam_mention_config['rate_limit']
    user_toggle = antispam_mention_config['user_toggle']
    group_toggle = antispam_mention_config['group_toggle']
    channel_toggle = antispam_mention_config['channel_toggle']
    bot_toggle = antispam_mention_config['bot_toggle']

    def get_toggle(b: bool) -> str:
        return '☂️ <i>On</i>' if b else '🌂 <i>Off</i>'

    user_toggle = get_toggle(user_toggle)
    group_toggle = get_toggle(group_toggle)
    channel_toggle = get_toggle(channel_toggle)
    bot_toggle = get_toggle(bot_toggle)
    rate_mentions = rate_limit['mentions']

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ 💬 <i>Blocco Menzioni</i>\n\n"
            "▫️ Da qui puoi gestire le <b>impostazioni</b> per il <b>blocco delle menzioni</b>.\n\n"
            f"🔸 <u>Stato</u>\n"
            f"      👤 <b>Utenti</b> – {user_toggle}\n"
            f"      👥 <b>Gruppi</b> – {group_toggle}\n"
            f"      📢 <b>Canali</b> – {channel_toggle}\n"
            f"      🤖 <b>Bot</b> – {bot_toggle}\n\n"
            f"🔸 <u>Consenti Dopo</u> – <i>{allow_after_text}</i>\n"
            f"🔸 <u>Rate-Limit</u> – <i>{pluralize(rate_mentions, 'Menzione', 'Menzioni')} in "
            f"{get_rate_limit_text(rate_limit['time'])}</i>\n\n"
            "🔹 Scegli un'opzione.")

    return text