from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem


async def render_admin_settings_management_panel(update: Update, context: CustomContext):
    text = _get_admin_settings_management_text()

    admin_settings_management_panel = Panel(
        PanelConfig(
            base_path="admin/manage_settings",
            text=text,
            keyboard=[
                [ButtonItem(text="🔔 Notifiche", callback_key="notifications")],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await admin_settings_management_panel.render(update=update, context=context)


def _get_header():
    text = ("⚙️ <b>Gestione Impostazioni</b>\n\n"
            "▫️ Da qui puoi gestire le impostazioni personali e quelle inerenti al gruppo.\n\n")
    return text


def _get_admin_settings_management_text():
    return _get_header() + "🔹 Scegli un'opzione."


async def render_admin_notification_settings_management_panel(update: Update, context: CustomContext):
    pass


def _get_admin_notification_settings_management_text():
    return _get_header() + ("      → 🔔 <i>Notifiche</i>\n\n"
                            "▫️ Da qui puoi gestire le notifiche che ricevi da parte del bot.\n\n"
                            "🔹 Scegli un'opzione.")