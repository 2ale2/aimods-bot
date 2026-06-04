from telegram import Update

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ChatType
from aimods_bot.src.helpers.constants.path_navigation import AntispamRoute, GlobalAction, SecurityFiltersRoute
from aimods_bot.src.helpers.constants.path_navigation.common import DigitRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import get_toggle_text, create_and_render_panel
from aimods_bot.src.helpers.utils.time_utils import get_allow_after_text, get_rate_limit_text, pluralize


async def render_antispam_mention_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = await _build_text(context)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [ButtonItem(text="#️⃣ Menzioni per Messaggio", callback_key=base_path.add(AntispamRoute.PER_MESSAGE))],
            [
                ButtonItem(text="👤 Utenti", callback_key=base_path.add(ChatType.USER)),
                ButtonItem(text="👥 Gruppi", callback_key=base_path.add(ChatType.GROUP)),
            ],
            [
                ButtonItem(text="📢 Canali", callback_key=base_path.add(ChatType.CHANNEL)),
                ButtonItem(text="🤖 Bot", callback_key=base_path.add(ChatType.BOT))
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


async def _build_text(context: CustomContext) -> str:
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


async def render_antispam_mention_per_message_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _build_per_message_text(context)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="1 Menzione", callback_key=base_path.add(DigitRoute.ONE)),
                ButtonItem(text="2 Menzioni", callback_key=base_path.add(DigitRoute.TWO)),
                ButtonItem(text="3 Menzioni", callback_key=base_path.add(DigitRoute.THREE))
            ],
            [
                ButtonItem(text="4 Menzioni", callback_key=base_path.add(DigitRoute.FOUR)),
                ButtonItem(text="5 Menzioni", callback_key=base_path.add(DigitRoute.FIVE)),
                ButtonItem(text="10 Menzioni", callback_key=base_path.add(DigitRoute.TEN))
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


def _build_per_message_text(context: CustomContext) -> str:
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


async def render_antispam_mention_category_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        chat_type: ChatType
):
    text = _build_mention_category_text(context=context, chat_type=chat_type)

    user_if_not_member = get_value(context, "moderation.antispam.mention.user.if_not_member")

    def get_toggle_if_not_member():
        return '✔' if user_if_not_member else '✖️'

    keyboard = [
        [
            ButtonItem(text="☂️ On", callback_key=base_path.add(GlobalAction.TOGGLE_ON)),
            ButtonItem(text="🌂 Off", callback_key=base_path.add(GlobalAction.TOGGLE_OFF))
        ],
        [ButtonItem(text="⚖️ Punizione", callback_key=base_path.add(SecurityFiltersRoute.PUNISHMENT))],
        [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
    ]

    if chat_type == ChatType.USER:
        keyboard.insert(1, [
            ButtonItem(
                text=f"🪪 Solo se non membro {get_toggle_if_not_member()}",
                callback_key=SecurityFiltersRoute.IF_NOT_MEMBER)
        ])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


def _build_mention_category_text(context: CustomContext, chat_type: ChatType) -> str:
    toggle = get_value(context=context, path=f"moderation.antispam.mention.{chat_type}.toggle")
    toggle_text = get_toggle_text(toggle)

    return ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ 💬 <i>Blocco Menzioni</i> – <i>Menzioni {chat_type.label}</i>\n\n"
            "▫️ Da qui puoi <b>disattivare completamente il controllo sull'intera categoria "
            f"<i>{chat_type.label}</i></b>.\n\n"
            f"🔸 <u>Toggle</u> – {toggle_text}\n\n"
            "🔹 Scegli un'opzione.")
