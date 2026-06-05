from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import UserNotifications
from aimods_bot.src.helpers.constants.constants import Platform
from aimods_bot.src.helpers.constants.path_navigation import UserManageSettingsRoute, GlobalAction
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.requests import PLATFORM_CATEGORY_REGISTRY
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel, chunk_buttons


async def render_user_settings_management_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    text = _get_user_settings_management_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [ButtonItem(text="🔔 Notifiche", callback_key=base_path.add(UserManageSettingsRoute.NOTIFICATIONS))],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


def _get_header():
    text = ("⚙️ <b>Gestione Impostazioni</b>\n\n"
            "▫️ Da qui puoi gestire le impostazioni personali.\n\n")
    return text


def _get_user_settings_management_text():
    return _get_header() + "🔹 Scegli un'opzione."


async def render_user_notification_settings_management_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    text = _get_user_notification_settings_management_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="📭 Apertura Sezioni",
                    callback_key=base_path.add(UserManageSettingsRoute.SECTION_OPENING_NOTIFICATIONS)
                )
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


def _get_user_notification_settings_management_text():
    return ("⚙️ <b>Gestione Impostazioni</b>\n\n"
            "      → 🔔 <i>Notifiche</i>\n\n"
            "▫️ Da qui puoi gestire le notifiche che ricevi da parte del bot.\n\n"
            "🔹 Scegli un'opzione.")


async def render_user_section_opening_notification_settings_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    settings = context.pydc.persistent.user_notifications
    text, keyboard = _get_user_section_opening_notification_settings_text_keyboard(
        settings=settings,
        base_path=base_path
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


def _get_user_section_opening_notification_settings_text_keyboard(settings: UserNotifications, base_path: PathBuilder):
    current_settings = settings.section_opening_notifications

    text = ("⚙️ <b>Gestione Impostazioni</b>\n\n"
            "      📭 <i>Notifiche</i> → <i><u>Apertura Sezioni</u></i>\n\n"
            "▫️ Da qui puoi gestire le notifiche sulle <b>aperture delle sezioni per le richieste</b>.\n\n"
            "        🗄 <b>Sezioni</b>\n")

    buttons = []

    for platform in Platform:
        text += f"              {platform.icon} <b>{platform.label}</b>\n"
        for cat, cat_conf in PLATFORM_CATEGORY_REGISTRY[platform].items():
            text += (f"                   🔸 <i>{cat_conf.label}</i> – "
                     f"{'🔔' if current_settings[platform][cat] else '🔕'}\n")
            buttons.append(
                ButtonItem(
                    text=f"{platform.icon} {cat_conf.label}",
                    callback_key=f"{platform.value}:{cat.value}")
            )

    keyboard = chunk_buttons(buttons=buttons, size=4)

    text += ("\n🔹 Riceverai <b>una notifica</b> ogni volta che una <b>sezione per le richieste</b> "
             "contrassegnata con una campanella <b>viene aperta</b>.")

    keyboard.append([ButtonItem(text="🔙 Conferma", callback_key=base_path.back())])

    return text, keyboard


async def render_section_opening_notification_disabled_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        section: RequestSection
):
    text = _get_section_opening_notification_disabled_text(section=section)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [ButtonItem(text="🚮 Chiudi", callback_key=GlobalAction.CLOSE)]
        ]
    )


def _get_section_opening_notification_disabled_text(section: RequestSection):
    cat_config = section.category_config
    text = ("✅ <b>Notifiche Disattivate</b>\n\n"
            "▫ <b>Non riceverai più le notifiche</b> inerenti all'apertura "
            f"della sezione {cat_config.icon} <b>{cat_config.label} ({section.platform.label})</b>.")

    return text
