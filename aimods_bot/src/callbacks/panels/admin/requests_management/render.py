from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem, Platform, Category, RequestData, \
    RequestStatus
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS, REQUEST_STATUS_DETAILS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.request_utils import get_active_category_requests, get_requests_summary, \
    get_request_details

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
    text = (f"{_get_header()}\n\n"
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


async def render_admin_active_requests_category_selector_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        platform: Platform
):
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

    admin_active_requests_category_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/active_requests/{platform.value}",
            text=text,
            keyboard=keyboard
        )
    )

    await admin_active_requests_category_panel.render(update=update, context=context)


def _get_admin_active_requests_category_text(platform: Platform):
    text = (f"{_get_header()}\n\n"
            f"→ 📕 <i>Richieste Attive {PLATFORM_DETAILS[platform.value]['label']}</i>\n\n"
            "🔹 Scegli una categoria.")
    return text


async def render_admin_active_requests_category_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        platform: Platform,
        category: Category
):
    requests = get_active_category_requests(context=context, platform=platform, category=category)
    text = _get_active_requests_category_text(platform=platform, category=category, requests=requests)

    keyboard = [[]]
    for n, el in enumerate(requests):
        if len(keyboard[-1]) == 2:
            keyboard.append([])
        keyboard[-1].append(ButtonItem(text=f"{n+1}", callback_key=el))

    back_button = ButtonItem(text="🔙 Indietro", callback_key=None)

    keyboard.append([back_button]) if len(requests) else keyboard[-1].append(back_button)

    admin_active_requests_category_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/active_requests/{platform.value}/{category.value}",
            text=text,
            keyboard=keyboard
        )
    )

    await admin_active_requests_category_panel.render(update=update, context=context)


def _get_active_requests_category_text(
        platform: Platform,
        category: Category,
        requests: dict[str, RequestData]
):
    pl_label = PLATFORM_DETAILS[platform.value]['label']
    ct_label = CATEGORY_DETAILS[platform.value][category.value]['label']
    text = (f"{_get_header()}\n\n"
            f"→ 📕 <i>Richieste Attive {pl_label} – {ct_label}</i>\n\n")

    text += get_requests_summary(requests=requests)

    if len(requests) == 0:
        text += "ℹ️ Non ci sono richieste attive per questa categoria."
    else:
        text += "\n🔹 Scegli la richiesta da gestire."

    return text


async def render_admin_manage_request_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        ix: str,
        request: RequestData):

    platform = request.get_platform()
    category = request.get_category()

    text = await _get_admin_manage_request_text(request=request, platform=platform, category=category)
    keyboard = _get_admin_menage_request_keyboard(request=request)

    admin_manage_request_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}",
            text=text,
            keyboard=keyboard
        )
    )

    await admin_manage_request_panel.render(update=update, context=context)


async def _get_admin_manage_request_text(
        request: RequestData,
        platform: Platform,
        category: Category
):
    pl_label = PLATFORM_DETAILS[platform.value]['label']
    ct_label = CATEGORY_DETAILS[platform.value][category.value]['label']
    text = (f"{_get_header()}\n\n"
            f"→ 📕 <i>Richieste Attive {pl_label} – {ct_label}</i>\n\n"
            "▪️ Da qui puoi gestire questa richiesta.\n\n")

    text += await get_request_details(request=request, admin=True)

    text += "\n🔹 Scegli un'opzione."

    return text


def _get_admin_menage_request_keyboard(request: RequestData):
    steps = [None, "pending", "examining", "testing", "completed", None]

    current_status = request.status.value
    current_index = steps.index(current_status)
    next_status_button = steps[current_index + 1]
    previous_status_button = steps[current_index - 1]

    keyboard = []
    if next_status_button:
        next_status_icon = REQUEST_STATUS_DETAILS[next_status_button]["icon"]
        next_status_label = REQUEST_STATUS_DETAILS[next_status_button]["label"]
        keyboard.insert(0, [ButtonItem(
            text=f"{next_status_icon} {next_status_label}",
            callback_key=next_status_button)
        ])
    if previous_status_button:
        previous_status_icon = REQUEST_STATUS_DETAILS[previous_status_button]["icon"]
        previous_status_label = REQUEST_STATUS_DETAILS[previous_status_button]["label"]
        keyboard.insert(0, [ButtonItem(
            text=f"{previous_status_icon} {previous_status_label}",
            callback_key=previous_status_button)
        ])

    keyboard.extend([
        [
            ButtonItem(text="❌ Rifiuta Richiesta", callback_key="rejected"),
            ButtonItem(text="🔄 Cambia Stato", callback_key="change_status")
        ],
        [ButtonItem(text="⛔️ Limita Utente", callback_key=f"limit_{request.user_id}")],
        [ButtonItem(text="🔙 Indietro", callback_key=None)]
    ])

    return keyboard


def _get_header():
    return "❔ <b>Gestione Richieste</b>"
