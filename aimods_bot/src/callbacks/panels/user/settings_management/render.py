from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import UserNotifications
from aimods_bot.src.helpers.constants.constants import CATEGORY_DETAILS, PLATFORM_DETAILS
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem


async def render_user_settings_management_panel(update: Update, context: CustomContext):
    text = _get_user_settings_management_text()

    user_settings_management_panel = Panel(
        PanelConfig(
            base_path="user/manage_settings",
            text=text,
            keyboard=[
                [ButtonItem(text="🔔 Notifiche", callback_key="notifications")],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await user_settings_management_panel.render(update=update, context=context)


def _get_header():
    text = ("⚙️ <b>Gestione Impostazioni</b>\n\n"
            "▫️ Da qui puoi gestire le impostazioni personali.\n\n")
    return text


def _get_user_settings_management_text():
    return _get_header() + "🔹 Scegli un'opzione."


async def render_user_notification_settings_management_panel(update: Update, context: CustomContext):
    text = _get_user_notification_settings_management_text()

    user_notification_settings_management_panel = Panel(
        PanelConfig(
            base_path="admin/manage_settings/notifications",
            text=text,
            keyboard=[
                [ButtonItem(text="📭 Apertura Sezioni", callback_key="section_opening")],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await user_notification_settings_management_panel.render(update=update, context=context)


def _get_user_notification_settings_management_text():
    return ("⚙️ <b>Gestione Impostazioni</b>\n\n"
            "      → 🔔 <i>Notifiche</i>\n\n"
            "▫️ Da qui puoi gestire le notifiche che ricevi da parte del bot.\n\n"
            "🔹 Scegli un'opzione.")


async def render_user_section_opening_notification_settings_panel(update: Update, context: CustomContext):
    settings = context.pydc.persistent.user_notifications
    text, keyboard = _get_user_section_opening_notification_settings_text_keyboard(settings=settings)

    user_new_requests_notification_settings_panel = Panel(
        PanelConfig(
            base_path="user/manage_settings/notifications/section_opening",
            text=text,
            keyboard=keyboard
        )
    )

    await user_new_requests_notification_settings_panel.render(update=update, context=context)


def _get_user_section_opening_notification_settings_text_keyboard(settings: UserNotifications):
    current_settings = settings.section_opening_notifications

    text = ("⚙️ <b>Gestione Impostazioni</b>\n\n"
            "      📭 <i>Notifiche</i> → <i><u>Apertura Sezioni</u></i>\n\n"
            "▫️ Da qui puoi gestire le notifiche sulle <b>aperture delle sezioni per le richieste</b>.\n\n"
            "        🗄 <b>Sezioni</b>\n")

    keyboard = [[]]

    for pl in CATEGORY_DETAILS:
        pl_icon = PLATFORM_DETAILS[pl]["icon"]
        pl_label = PLATFORM_DETAILS[pl]["label"]
        text += f"              {pl_icon} <b>{pl_label}</b>\n"
        for ca in CATEGORY_DETAILS[pl]:
            ca_label = CATEGORY_DETAILS[pl][ca]["label"]
            text += f"                   🔸 <i>{ca_label}</i> – {'🔔' if current_settings[pl][ca] else '🔕'}\n"
            if len(keyboard[-1]) >= 4:
                keyboard.append([])
            keyboard[-1].append(ButtonItem(text=f"{pl_icon} {ca_label}", callback_key=f"{pl}:{ca}"))

    text += ("\n🔹 Riceverai <b>una notifica</b> ogni volta che una <b>sezione per le richieste</b> contrassegnata con "
             "una campanella <b>viene aperta</b>.")

    keyboard.append([ButtonItem(text="🔙 Conferma", callback_key=None)])

    return text, keyboard


async def render_section_opening_notification_disabled_panel(update: Update, context: CustomContext, data: str):
    text = _get_section_opening_notification_disabled_text(data=data)

    new_requests_notification_disabled_panel = Panel(
        PanelConfig(
            base_path="user",
            text=text,
            keyboard=[
                [ButtonItem(text="🚮 Chiudi", callback_key="close_menu")]
            ]
        )
    )

    await new_requests_notification_disabled_panel.render(update=update, context=context)


def _get_section_opening_notification_disabled_text(data: str):
    pl, ca = data.split(":")
    pl_label = PLATFORM_DETAILS[pl]["label"]
    ca_label = CATEGORY_DETAILS[pl][ca]["label"]
    ca_icon = CATEGORY_DETAILS[pl][ca]["icon"]

    text = ("✅ <b>Notifiche Disattivate</b>\n\n"
            "▫ <b>Non riceverai più le notifiche</b> inerenti all'apertura "
            f"della sezione {ca_icon} <b>{ca_label} ({pl_label})</b>.")

    return text
