from telegram import Update

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ChatType
from aimods_bot.src.helpers.constants.path_navigation import SecurityFiltersRoute, GlobalAction
from aimods_bot.src.helpers.constants.path_navigation.moderation import ForwardRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import get_toggle_text, create_and_render_panel
from aimods_bot.src.helpers.utils.time_utils import get_allow_after_text


async def render_antispam_forward_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _get_text(context)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="⏳ Consenti Dopo", callback_key=base_path.add(SecurityFiltersRoute.ALLOW_AFTER)),
            ],
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


# TODO: da tipizzare
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


async def render_antispam_forward_category_panel(
        update: Update, 
        context: CustomContext,
        base_path: PathBuilder,
        chat_type: ChatType
):
    text = await _get_category_text(context, chat_type)

    user_if_not_member = get_value(context, "moderation.antispam.forward.user.if_not_member")

    def get_toggle_if_not_member():
        return '✔' if user_if_not_member else '✖️'

    keyboard = [
        [
            ButtonItem(text="☂️ On", callback_key=base_path.add(GlobalAction.TOGGLE_ON)),
            ButtonItem(text="🌂 Off", callback_key=base_path.add(GlobalAction.TOGGLE_ON))
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


async def _get_category_text(context: CustomContext, chat_type: ChatType) -> str:
    toggle = get_value(context, f"moderation.antispam.forward.{chat_type.value}.toggle")
    toggle_text = get_toggle_text(toggle)

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ {chat_type.icon} <i>Blocco Inoltri</i> – <i>{chat_type.label}</i>\n\n"
            "▫️ Da qui puoi gestire le impostazioni relative "
            f"agli inoltri di messaggi provenienti da {chat_type.label.lower()}.\n\n"
            f"🔸 <u>Toggle</u> – {toggle_text}\n\n"
            "🔹 Scegli un'opzione.")

    return text


async def render_antispam_forward_rate_limit_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _get_rate_limit_text(context)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="⏳ Timespan", callback_key=base_path.add(ForwardRoute.TIMESPAN)),
                ButtonItem(text="👤 Per Utente", callback_key=base_path.add(ForwardRoute.PER_USER))
            ],
            [
                ButtonItem(text="💬 Per Contenuto", callback_key=base_path.add(ForwardRoute.PER_CONTENT)),
                ButtonItem(text="📤 Per Fonte", callback_key=base_path.add(ForwardRoute.PER_SOURCE))
            ]
        ]
    )


def _get_rate_limit_text(context: CustomContext):
    config = get_value(context=context, path="moderation.antispam.forward.rate_limit")
    timespan = config["timespan"]
    same_content = config["same_content"]
    same_source = config["same_source"]
    same_user = config["same_user"]

    return ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            "↦ ⏱️ <i>Blocco Inoltri</i> – <i>Rate Limit</i>\n\n"
            "▫️ Da qui puoi impostare il rate limiting per gli inoltri.\n\n"
            f"🔸 <u>Timespan</u> – <i>{timespan} secondi</i>\n"
            f"🔸 <u>Stesso Contenuto</u> – <i>{same_content} messaggi</i>\n"
            f"🔸 <u>Stesso Utente</u> – <i>{same_user} messaggi</i>\n"
            f"🔸 <u>Stessa Fonte</u> – <i>{same_source} messaggi</i>\n\n"
            "🔹 Scegli un'opzione.")
