from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem, Platform
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("admin_requests_management_render")


async def render_admin_request_management_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _get_admin_request_management_text()

    admin_request_management_panel = Panel(
        PanelConfig(
            base_path="admin/manage_requests",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="📕 Richieste Attive", callback_key="active_requests"),
                    ButtonItem(text="⏯️ Gestione Topic", callback_key="manage_topics")
                ],
                [
                    ButtonItem(text="⛔️ Limita Utente", callback_key="limit_user_request"),
                    ButtonItem(text="🔙 Indietro", callback_key=None)
                ]
            ]
        )
    )

    await admin_request_management_panel.render(update=update, context=context)


def _get_admin_request_management_text():
    text = (f"{_get_header()}"
            "▪️ Da qui puoi gestire le richieste attive e settare le impostazioni per sui limiti delle richieste.\n\n"
            "🔹 Scegli un'opzione.")
    return text


async def render_admin_active_requests_management_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _get_admin_request_management_text()

    keyboard = [[]]
    for el in PLATFORM_DETAILS:
        item = PLATFORM_DETAILS[el]
        icon = item["icon"]
        label = item["label"]

        if len(keyboard[-1]) == 2:
            keyboard.append([])

        keyboard[-1].append(ButtonItem(text=f"{icon} {label}", callback_key=el))

    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=None)])

    admin_active_requests_management_panel = Panel(
        PanelConfig(
            base_path="admin/manage_requests/active_requests",
            text=text,
            keyboard=keyboard
        )
    )

    await admin_active_requests_management_panel.render(update=update, context=context)


def _get_admin_active_requests_management_text():
    text = (f"{_get_header()}\n\n"
            "→ 📕 <i>Richieste Attive</i>\n\n"
            "🔹 Scegli una piattaforma.")
    return text


async def render_admin_active_requests_category_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, platform: Platform):
    text = _get_admin_active_requests_category_text(platform=platform)

    categories = CATEGORY_DETAILS.get(platform.value, None)
    if not categories:
        log.error(f"La piattaforma {platform.value} non è in constants.CATEGORY_DETAILS.")
        return None

    keyboard = [[]]
    for el in categories:
        category = categories[el]
        icon = category["icon"]
        label = category["label"]

        if len(keyboard[-1]) == 2:
            keyboard.append([])

        keyboard[-1].append(ButtonItem(text=f"{icon} {label}", callback_key=el))

    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=None)])


def _get_admin_active_requests_category_text(platform: Platform):
    text = (f"{_get_header()}\n\n"
            f"→ 📕 <i>Richieste Attive {PLATFORM_DETAILS[platform.value]['label']}</i>\n\n"
            "🔹 Scegli una categoria.")
    return text


def _get_header():
    return "❔ <b>Gestione Richieste</b>"
