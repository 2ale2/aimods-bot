from telegram import Update

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.constants.constants import PUNISHMENT_EMOJIS, MODERATION_DISPLAY_ITEMS
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel
from aimods_bot.src.helpers.utils.time_utils import sec_value_limited, get_duration_text


async def render_punishment_panel(update: Update, context: CustomContext, setting: str):
    text = await _build_punishment_text(context=context, setting=setting)

    if update.callback_query:
        raw_data = update.callback_query.data
        p = raw_data.split("/")
        if "punishment" in p:
            idx = p.index("punishment")
            data = "/".join(p[:idx + 1])
        else:
            data = raw_data
    else:
        data = f"moderation/security_filters/{setting}/punishment"

    keyboard = [
        [ButtonItem(text="⏳ Imposta Durata Punizione", callback_key="duration")],
        [
            ButtonItem(text="🚫 Ban", callback_key="ban"),
            ButtonItem(text="🥊 Kick", callback_key="kick")
        ],
        [
            ButtonItem(text="🔒 Mute", callback_key="mute"),
            ButtonItem(text="⚠️ Warn", callback_key="warn")
        ],
        [ButtonItem(text="🔙 Indietro", callback_key=None)]
    ]

    s = setting.split("/")
    if len(s) > 1:
        main_settings = s[0]
        name_item = MODERATION_DISPLAY_ITEMS[main_settings].display_name
        keyboard.insert(0, [ButtonItem(text=f"🧞 Stessa Punizione {name_item}", callback_key=main_settings)])

    temp_data = context.chat_data.get('setting_duration')
    message_id = None
    if temp_data:
        message_id = temp_data.get('message_id')
        context.chat_data.pop('setting_duration')

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=data,
        text=text,
        keyboard=keyboard,
        message_id=message_id
    )


async def render_punishment_duration_panel(update: Update, context: CustomContext, setting: str):
    text = _build_punishment_duration_text(setting=setting)

    context.chat_data['setting_duration'] = {'setting': setting, 'message_id': update.effective_message.message_id}

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=update.callback_query.data,
        text=text,
        keyboard=[
            [ButtonItem(text="♾️ Tempo Indeterminato", callback_key="endless")],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


async def _build_punishment_text(context: CustomContext, setting: str):
    config = get_value(context, f"moderation.{setting.replace('/', '.')}")
    time_total_seconds = config["punishment"]["time"]
    punishment = config["punishment"]["type"]

    punishment_limited = sec_value_limited(time_total_seconds)
    time_text = (
        get_duration_text(time_total_seconds) if punishment_limited
        else "♾️ A Tempo Indeterminato"
    )

    display_item = MODERATION_DISPLAY_ITEMS.get(setting)
    display_icon = display_item.display_icon
    display_name = display_item.display_name
    target_description = display_item.target_description

    text = (f"{display_icon} <b>Impostazioni {display_name}</b>\n\n"
            "↦ ⚖️ <i>Impostazioni Punizione</i>\n\n"
            f"▫️ Qui puoi configurare la punizione comminata {target_description}.\n\n"
            f"🔸 <u>Punizione</u> – {PUNISHMENT_EMOJIS[punishment]} <i>{punishment.capitalize()}</i>\n"
            f"🔸 <u>Tempo</u> – <i>{time_text}</i>\n\n"
            f"🔹 Scegli un'opzione.")

    return text


def _build_punishment_duration_text(setting: str):
    display_item = MODERATION_DISPLAY_ITEMS.get(setting)
    display_icon = display_item.display_icon
    display_name = display_item.display_name
    target_description = display_item.target_description

    text = (f"{display_icon} <b>Impostazioni {display_name}</b>\n\n"
            "↦ 🕔 <i>Tempo Punizione</i>\n\n"
            f"▫️ Puoi impostare da qui la durata della punizione comminata {target_description}.\n\n"
            "❓ Indica una durata del tipo <code>52 giorni 4 ore 100 minuti 20 secondi</code>.\n\n"
            "ℹ️ Il tempo non viene considerato se la punizione scelta è <i>Kick</i>.")

    return text
