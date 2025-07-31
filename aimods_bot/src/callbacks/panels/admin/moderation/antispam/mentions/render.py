from pyrogram.types import InlineKeyboardButton
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
                [ButtonItem(text="⏱️ Rate Limit", callback_key="rate_limit")],
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
    user_toggle = antispam_mention_config['user']
    group_toggle = antispam_mention_config['group']
    channel_toggle = antispam_mention_config['channel']
    bot_toggle = antispam_mention_config['bot']
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
            f"🔸 <u>Menzioni per Messaggio</u> – <i>{pluralize(per_message, 'Menzione', 'Menzioni')}</i>\n"
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
                ],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await antispam_mention_per_message_panel.render(update=update, context=context)


def _build_per_message_text(context: CallbackContext) -> str:
    antispam_mention_config = get_value(context, "moderation.antispam.mention")
    per_message = antispam_mention_config['per_message']

    text = (
        "📨 <b>Impostazioni Anti-Spam</b>\n\n"
        "↦ ⏱️ <i>Blocco Menzioni</i> – <i>Menzioni Per Messaggio</i>\n\n"
        "▫ Indica il <b>numero di menzioni che possono essere inserite in un unico messaggio</b>. "
        "La <b>violazione</b> di questo limite comporta il <b>ban immediato</b>, a prescindere dall'impostazione "
        "settata per l'antispam. Le menzioni presenti in Whitelist non vengono conteggiate.\n\n"
        f"🔸 <u>Menzioni per Messaggio</u> – <i>{pluralize(per_message, 'Menzione', 'Menzioni')} "
        "per Messaggio</i>\n\n"
        "🔹 Scegli un'opzione."
    )

    return text


async def render_antispam_mention_category_panel(update: Update, context: CallbackContext, category: str):
    text = _build_mention_category_text(context=context, category=category)

    user_if_not_member = get_value(context, "moderation.antispam.mention.user_if_not_member")

    def get_toggle_if_not_member():
        return '👍' if user_if_not_member else '👎'

    def get_if_not_member_data():
        return "if_not_member_true" if user_if_not_member else "if_not_member_false"

    keyboard = [
        [
            ButtonItem(text="☂️ On", callback_key="on"),
            ButtonItem(text="🌂 Off", callback_key="off")
        ],
        [ButtonItem(text="⚖️ Punizione", callback_key="punishment")],
        [ButtonItem(text="🔙 Indietro", callback_key=None)]
    ]

    if category == "user":
        keyboard.insert(1, [
            ButtonItem(
                text=f"🪪 Solo se non membro {get_toggle_if_not_member()}",
                callback_key=get_if_not_member_data())
        ])

    antispam_mention_category_panel = Panel(
        PanelConfig(
            base_path=f"moderation/security_filters/antispam/mention/{category}",
            text=text,
            keyboard=keyboard
        )
    )

    await antispam_mention_category_panel.render(update=update, context=context)


def _build_mention_category_text(context: CallbackContext, category: str) -> str:
    map_to_word = {
        "user": "Utenti",
        "group": "Gruppi",
        "channel": "Canali",
        "bot": "Bot"
    }
    word = map_to_word[category]
    toggle = get_value(context=context, path=f"moderation.antispam.mention.{category}")
    toggle_text = get_toggle_text(toggle)

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ 💬 <i>Blocco Menzioni</i> – <i>Menzioni {word}</i>\n\n"
            f"▫️ Da qui puoi <b>disattivare completamente il controllo sull'intera categoria <i>{word}</i></b>.\n\n"
            f"🔸 <u>Toggle</u> – {toggle_text}\n\n"
            f"🔹 Scegli un'opzione.")

    return text
