from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import CATEGORY_DETAILS, PLATFORM_DETAILS
from aimods_bot.src.helpers.models.ui import ButtonItem

from aimods_bot.src.helpers.constants.conversation_paths.navigation import AdminSettingsRoute, \
    AdminSettingsNotificationsRoute, AdminRoute, GlobalAction
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel, chunk_buttons


# --- HELPER CONDIVISI ---

def _build_notification_ui(
        settings_dict: dict,
        header_title: str,
        description: str,
        footer_info: str,
        base_path: PathBuilder
):
    """
    Costruisce dinamicamente il testo ad albero e la tastiera a griglia per le impostazioni di notifica.
    """
    text_parts = [
        "⚙️ <b>Gestione Impostazioni</b>\n\n",
        f"      {header_title}\n\n",
        f"▫️ {description}\n\n",
        "        🗄 <b>Sezioni</b>\n"
    ]

    buttons = []

    for pl, pl_data in PLATFORM_DETAILS.items():
        text_parts.append(f"              {pl_data['icon']} <b>{pl_data['label']}</b>\n")

        categories = CATEGORY_DETAILS.get(pl, {})
        for ca, ca_data in categories.items():
            is_active = settings_dict[pl][ca]
            status_icon = '🔔' if is_active else '🔕'
            text_parts.append(f"                   🔸 <i>{ca_data['label']}</i> – {status_icon}\n")

            buttons.append(ButtonItem(
                text=f"{pl_data['icon']} {ca_data['label']}",
                callback_key=base_path.add(f"{pl}:{ca}"))
            )

    keyboard = chunk_buttons(buttons=buttons, size=4)

    text_parts.append(f"\n{footer_info}")

    keyboard.append([ButtonItem(text="🔙 Conferma", callback_key=base_path.back())])

    return "".join(text_parts), keyboard


def _get_disabled_panel_text(data: str, context_topic: str) -> str:
    """Genera il testo per i pannelli di conferma disabilitazione."""
    pl, ca = data.split(":")
    pl_label = PLATFORM_DETAILS[pl]["label"]
    ca_label = CATEGORY_DETAILS[pl][ca]["label"]
    ca_icon = CATEGORY_DETAILS[pl][ca]["icon"]

    return (
        "✅ <b>Notifiche Disattivate</b>\n\n"
        f"▫ <b>Non riceverai più le notifiche</b> inerenti {context_topic} "
        f"per la sezione {ca_icon} <b>{ca_label} ({pl_label})</b>."
    )


# --- RENDERING PANEL PRINCIPALI ---

async def render_admin_settings_management_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    text = _get_admin_settings_management_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [ButtonItem(text="🔔 Notifiche", callback_key=base_path.add(AdminSettingsRoute.NOTIFICATIONS))],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


def _get_admin_settings_management_text():
    return ("⚙️ <b>Gestione Impostazioni</b>\n\n"
            "▫️ Da qui puoi gestire le impostazioni personali e quelle inerenti al gruppo.\n\n"
            "🔹 Scegli un'opzione.")


async def render_admin_notification_settings_management_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    text = _get_admin_notification_settings_management_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="📥 Nuove Richieste",
                    callback_key=base_path.add(AdminSettingsNotificationsRoute.NEW_REQUESTS)
                ),
                ButtonItem(
                    text="📪 Chiusura Sezioni",
                    callback_key=base_path.add(AdminSettingsNotificationsRoute.SECTION_CLOSING)
                )
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


def _get_admin_notification_settings_management_text():
    return ("⚙️ <b>Gestione Impostazioni</b>\n\n"
            "      → 🔔 <i>Notifiche</i>\n\n"
            "▫️ Da qui puoi gestire le notifiche che ricevi da parte del bot.\n\n"
            "🔹 Scegli un'opzione.")


# --- RENDERING SPECIFICI (New Requests) ---

async def render_admin_new_requests_notification_settings_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    settings = context.pydc.persistent.admin_notifications.new_requests_notifications

    text, keyboard = _build_notification_ui(
        base_path=base_path,
        settings_dict=settings,
        header_title="📥 <i>Notifiche</i> → <i><u>Nuove Richieste</u></i>",
        description="Da qui puoi gestire le notifiche sulle <b>nuove richieste</b>.",
        footer_info=("🔹 Riceverai <b>una notifica</b> ogni volta che un utente formulerà una "
                     "<b>nuova richiesta</b> per le sezioni contrassegnate con la campanella.")
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


async def render_new_requests_notification_disabled_panel(update: Update, context: CustomContext, data: str):
    text = _get_disabled_panel_text(data, "alle nuove richieste")

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=PathBuilder(AdminRoute.ROOT),
        text=text,
        keyboard=[[ButtonItem(text="🚮 Chiudi", callback_key=PathBuilder(GlobalAction.CLOSE_MENU))]]
    )


# --- RENDERING SPECIFICI (Section Closing) ---

async def render_admin_section_closing_notification_settings_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    settings = context.pydc.persistent.admin_notifications.section_closing_notifications

    text, keyboard = _build_notification_ui(
        base_path=base_path,
        settings_dict=settings,
        header_title="📪 <i>Notifiche</i> → <i><u>Chiusura Sezioni</u></i>",
        description="Da qui puoi gestire le notifiche sulla <b>chiusura delle sezioni</b>.",
        footer_info=("<blockquote>ℹ <b>Info</b> – Riceverai <b>una notifica</b> ogni volta che una "
                     "<b>sezione</b> contrassegnata con 🔔 verrà <b>chiusa automaticamente dal bot</b>."
                     "</blockquote>\n\n🔹 Scegli un'opzione.")
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


async def render_section_closure_notification_disabled_panel(update: Update, context: CustomContext, data: str):
    text = _get_disabled_panel_text(data, "alla chiusura")

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=PathBuilder(AdminRoute.ROOT),
        text=text,
        keyboard=[[ButtonItem(text="🚮 Chiudi", callback_key=PathBuilder(GlobalAction.CLOSE_MENU))]]
    )
