from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import get_toggle_text
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
                [ButtonItem(text="#️⃣ Menzioni per Messaggio", callback_key="per_message")],
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
    per_message = antispam_mention_config['per_message']

    user_toggle = get_toggle_text(user_toggle)
    group_toggle = get_toggle_text(group_toggle)
    channel_toggle = get_toggle_text(channel_toggle)
    bot_toggle = get_toggle_text(bot_toggle)
    rate_mentions = rate_limit['mention']

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ 💬 <i>Blocco Menzioni</i>\n\n"
            "▫️ Da qui puoi gestire le <b>impostazioni</b> per il <b>blocco delle menzioni</b>.\n\n"
            f"🔸 <u>Stato</u>\n"
            f"      👤 <b>Utenti</b> – {user_toggle}\n"
            f"      👥 <b>Gruppi</b> – {group_toggle}\n"
            f"      📢 <b>Canali</b> – {channel_toggle}\n"
            f"      🤖 <b>Bot</b> – {bot_toggle}\n\n"
            f"🔸 <u>Consenti Dopo</u> – <i>{allow_after_text}</i>\n"
            f"🔸 <u>Menzioni per Messaggio</u> – <i>{pluralize(per_message, 'Menzione', 'Menzione')}</u>\n\n"
            f"🔸 <u>Rate-Limit</u> – <i>{pluralize(rate_mentions, 'Menzione', 'Menzioni')} in "
            f"{get_rate_limit_text(rate_limit['time'])}</i>\n\n"
            "🔹 Scegli un'opzione.")

    return text


async def render_antispam_mention_per_message_panel(update: Update, context: CallbackContext):
    text = _build_per_message_text(context)

    antispam_mention_per_message_panel = Panel(
        PanelConfig(
            base_path="moderation/security_filters/antispam/mention/per_message",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="1 Menzione", callback_key="1"),
                    ButtonItem(text="2 Menzioni", callback_key="2"),
                    ButtonItem(text="3 Menzioni", callback_key="3")
                ],
                [
                    ButtonItem(text="4 Menzioni", callback_key="4"),
                    ButtonItem(text="5 Menzioni", callback_key="5"),
                    ButtonItem(text="10 Menzioni", callback_key="10")
                ]
            ]
        )
    )

    await antispam_mention_per_message_panel.render(update=update, context=context)


def _build_per_message_text(context: CallbackContext) -> str:
    antispam_mention_config = get_value(context, "moderation.antispam.mention")
    per_message = antispam_mention_config['per_message']

    text = (
        "📨 <b>Impostazioni Anti-Spam</b>\n\n"
        f"↦ ⏱️ <i>Blocco Menzioni</i> – <i>Menzioni Per Messaggio</i>\n\n"
        "▫ Indica il numero di menzioni che possono essere inserite in un unico messaggio."
        "La violazione di questo limite comporta il ban immediato, a prescindere dall'impostazione settata per "
        "l'antispam. Le menzioni presenti in Whitelist non vengono conteggiate.\n\n"
        f"🔸 <u>Menzioni per Messaggio</u> – {pluralize(per_message, 'Menzione', 'Menzioni')} per Messaggio\n\n"
    )

    return text
