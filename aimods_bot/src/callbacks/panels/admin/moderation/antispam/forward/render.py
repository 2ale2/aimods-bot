from telegram import Update

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.models import PanelConfig, Panel, ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import get_toggle_text
from aimods_bot.src.helpers.utils.time_utils import get_allow_after_text


async def render_antispam_forward_panel(update: Update, context: CustomContext):
    text = _get_text(context)

    antispam_forward_panel = Panel(
        PanelConfig(
            base_path="moderation/security_filters/antispam/forward",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="⏳ Consenti Dopo", callback_key="allow_after"),
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

    await antispam_forward_panel.render(update=update, context=context)


def _get_text(context: CustomContext) -> str:
    antispam_forward_configuration = get_value(context, "moderation.antispam.forward")

    allow_after = antispam_forward_configuration["allow_after"]

    user = antispam_forward_configuration["user"]
    group = antispam_forward_configuration["group"]
    channel = antispam_forward_configuration["channel"]
    bot = antispam_forward_configuration["bot"]

    user_toggle = get_toggle_text(user["toggle"])
    group_toggle = get_toggle_text(group["toggle"])
    channel_toggle = get_toggle_text(channel["toggle"])
    bot_toggle = get_toggle_text(bot["toggle"])

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ 👥 <i>Blocco Inoltri</i>\n\n"
            "▫️ Da qui puoi gestire le <b>impostazioni</b> per il <b>blocco degli inoltri</b>.\n\n"
            f"🔸 <u>Stato</u>\n"
            f"      👤 <b>Utenti</b> – {user_toggle}\n"
            f"      👥 <b>Gruppi</b> – {group_toggle}\n"
            f"      📢 <b>Canali</b> – {channel_toggle}\n"
            f"      🤖 <b>Bot</b> – {bot_toggle}\n\n"
            f"🔸 Consenti Dopo – <i>{get_allow_after_text(allow_after)}</i>\n\n"
            "🔹 Scegli un'opzione.")

    return text


async def render_antispam_forward_category_panel(update: Update, context: CustomContext, category: str):
    text = await _get_category_text(context, category)

    user_if_not_member = get_value(context, "moderation.antispam.forward.user.if_not_member")

    def get_toggle_if_not_member():
        return '✔' if user_if_not_member else '✖️'

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
                callback_key='if_not_member')
        ])

    antispam_forward_category_panel = Panel(
        PanelConfig(
            base_path=f"moderation/security_filters/antispam/forward/{category}",
            text=text,
            keyboard=keyboard
        )
    )

    await antispam_forward_category_panel.render(update=update, context=context)


async def _get_category_text(context: CustomContext, category: str) -> str:
    map_to_word = {
        "user": "Utenti",
        "group": "Gruppi",
        "channel": "Canali",
        "bot": "Bot"
    }
    toggle = get_value(context, f"moderation.antispam.forward.{category}.toggle")
    word = map_to_word[category]
    toggle_text = get_toggle_text(toggle)

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ 👥 <i>Blocco Inoltri</i> – <i>{word}</i>\n\n"
            "▫️ Da qui puoi gestire le impostazioni relative "
            f"agli inoltri di messaggi provenienti da {word.lower()}.\n\n"
            f"🔸 <u>Toggle</u> – {toggle_text}\n\n"
            "🔹 Scegli un'opzione.")

    return text


async def render_antispam_forward_rate_limit_panel(update: Update, context: CustomContext):
    text = _get_rate_limit_text(context)

    antispam_forward_rate_limit_panel = Panel(
        PanelConfig(
            base_path="moderation/security_filters/antispam/forward/rate_limit",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="⏳ Timespan", callback_key="timespan"),
                    ButtonItem(text="👤 Per Utente", callback_key="same_user")
                ],
                [
                    ButtonItem(text="💬 Per Contenuto", callback_key="same_content"),
                    ButtonItem(text="📤 Per Fonte", callback_key="same_source")
                ]
            ]
        )
    )

    await antispam_forward_rate_limit_panel.render(update=update, context=context)


def _get_rate_limit_text(context: CustomContext):
    config = get_value(context=context, path="moderation.antispam.forward.rate_limit")
    timespan = config["timespan"]
    same_content = config["same_content"]
    same_source = config["same_source"]
    same_user = config["same_user"]

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ ⏱️ <i>Blocco Inoltri</i> – <i>Rate Limit</i>\n\n"
            "▫️ Da qui puoi impostare il rate limiting per gli inoltri.\n\n"
            f"🔸 <u>Timespan</u> – <i>{timespan} secondi</i>\n"
            f"🔸 <u>Stesso Contenuto</u> – <i>{same_content} messaggi</i>\n"
            f"🔸 <u>Stesso Utente</u> – <i>{same_user} messaggi</i>\n"
            f"🔸 <u>Stessa Fonte</u> – <i>{same_source} messaggi</i>\n\n"
            "🔹 Scegli un'opzione.")

    return text