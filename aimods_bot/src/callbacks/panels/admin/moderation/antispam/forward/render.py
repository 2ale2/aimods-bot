from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.helpers.constants.models import PanelConfig, Panel, ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import get_toggle_text
from aimods_bot.src.helpers.utils.time_utils import get_allow_after_text, sec_value_limited, get_time_text
from aimods_bot.src.helpers.constants.constants import PUNISHMENT_EMOJIS


async def render_antispam_forward_panel(update: Update, context: CallbackContext):
    text = _get_text(context)

    antispam_forward_panel = Panel(
        PanelConfig(
            base_path="moderation/security_filters/moderation/antispam/forward",
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


def _get_text(context: CallbackContext) -> str:
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


async def render_antispam_forward_category_panel(update: Update, context: CallbackContext, category: str):
    pass


async def _get_category_text(context: CallbackContext, category: str) -> str:
    map_to_word = {
        "user": "Utenti",
        "group": "Gruppi",
        "channel": "Canali",
        "bot": "Bot"
    }
    item = get_value(context, f"moderation.antispam.forward.{category}")
    toggle = item["toggle"]
    punishment = item["punishment"]
    punishment_type = punishment["type"]
    punishment_time = punishment["time"]
    if_member = item.get("if_member", None)
    word = map_to_word[category]
    toggle_text = get_toggle_text(toggle)

    punishment_limited = sec_value_limited(punishment_time)
    time_text = (
        await get_time_text(punishment_time) if punishment_limited
        else "♾️ A Tempo Indeterminato"
    )

    text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ 👥 <i>Blocco Inoltri</i> – <i>{word}</i>\n\n"
            f"▫️ Da qui puoi gestire le impostazioni relative "
            f"agli inoltri di messaggi provenienti da {word.lower()}.\n\n"
            f"🔸 <u>Toggle</u> – {toggle_text}\n"
            f"🔸 <u>Punizione</u> – {PUNISHMENT_EMOJIS[punishment_type]} <i>{punishment_type.capitalize()}</i>\n"
            f"🔸 <u>Tempo Punizione</u> – <i>{time_text}</i>\n")
