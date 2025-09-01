from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS, REQUEST_STATUS_DETAILS
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem, Platform, Category, RequestData, \
    RequestStatus
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.request_utils import get_active_category_requests, get_requests_summary, \
    get_request_details, get_platform_categories

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

    if len(categories) == 1:
        category = get_platform_categories(platform=platform)(list(categories.keys())[0])

        return await render_admin_active_requests_category_panel(
            update=update,
            context=context,
            platform=platform,
            category=category
        )

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

    categories = get_platform_categories(platform=platform)
    if len(categories) > 1:
        back_button_callback_key = f"admin/manage_requests/active_requests/{platform.value}"
    else:
        back_button_callback_key = f"admin/manage_requests/active_requests"

    if len(requests) == 1:
        ix = list(requests.keys())[0]
        request_data = requests[ix]

        return await render_admin_manage_request_panel(
            update=update,
            context=context,
            ix=ix,
            request=request_data,
            back_button_callback_key=back_button_callback_key
        )

    text = _get_active_requests_category_text(platform=platform, category=category, requests=requests)

    keyboard = [[]]
    for n, el in enumerate(requests):
        if len(keyboard[-1]) == 2:
            keyboard.append([])
        keyboard[-1].append(ButtonItem(text=f"{n+1}", callback_key=el))

    back_button = ButtonItem(
        text="🔙 Indietro", 
        callback_key=back_button_callback_key, 
        override_path_generation=(back_button_callback_key is not None)
    )

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
        request: RequestData,
        back_button_callback_key: str = None
):

    platform = request.get_platform()
    category = request.get_category()

    text = await _get_admin_manage_request_text(request=request, platform=platform, category=category)
    keyboard = _get_admin_menage_request_keyboard(request=request, back_button_callback_key=back_button_callback_key)

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

    status = request.status

    text += await get_request_details(request=request, admin=True)

    if status is RequestStatus.COMPLETED:
        text += ("\n<blockquote>ℹ Lo stato di questa richiesta non può essere cambiato perché è stata già "
                 "contrassegnata come completata.</blockquote>\n")

    text += "\n🔹 Scegli un'opzione."

    return text


def _get_admin_menage_request_keyboard(request: RequestData, back_button_callback_key: str = None):
    steps = [None] + [el.value for el in RequestStatus] + [None]

    current_status = request.status
    current_status_value = current_status.value
    current_index = steps.index(str(current_status_value))
    next_status_button = steps[current_index + 1]
    previous_status_button = steps[current_index - 1]

    keyboard = [[]]
    if current_status is not RequestStatus.COMPLETED:
        if next_status_button:
            next_status_icon = REQUEST_STATUS_DETAILS[next_status_button]["icon"]
            next_status_label = REQUEST_STATUS_DETAILS[next_status_button]["label"]
            keyboard[0].insert(0, ButtonItem(
                text=f"{next_status_icon} {next_status_label}",
                callback_key=next_status_button)
            )
        if previous_status_button:
            previous_status_icon = REQUEST_STATUS_DETAILS[previous_status_button]["icon"]
            previous_status_label = REQUEST_STATUS_DETAILS[previous_status_button]["label"]
            keyboard[0].insert(0, ButtonItem(
                text=f"{previous_status_icon} {previous_status_label}",
                callback_key=previous_status_button)
            )

        keyboard.extend([
            [
                ButtonItem(text="❌ Rifiuta Richiesta", callback_key="rejected"),
                ButtonItem(text="🔄 Cambia Stato", callback_key="change_status")
            ]
        ])

    keyboard.extend([
        [ButtonItem(text="⛔️ Limita Utente", callback_key=f"limit_{request.user_id}")],
        [ButtonItem(
            text="🔙 Indietro",
            callback_key=back_button_callback_key,
            override_path_generation=(back_button_callback_key is not None)
        )]
    ])

    if current_status is RequestStatus.COMPLETED:
        keyboard[-2].insert(0, ButtonItem(
            text="🚮 Rimuovi da Attive", callback_key="remove"
        ))

    return keyboard


async def render_change_request_status_confirmation_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        ix: str,
        request: RequestData,
        status: RequestStatus
):
    platform = request.get_platform()
    category = request.get_category()
    text = await _get_render_change_request_status_confirmation_text(
        platform=platform,
        category=category,
        request=request,
        status=status
    )

    change_request_status_confirmation_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}/{status.value}",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="✅ Conferma", callback_key="yes"),
                    ButtonItem(text="🔙 Annulla", callback_key=None)
                ]
            ]
        )
    )

    await change_request_status_confirmation_panel.render(update=update, context=context)


async def _get_render_change_request_status_confirmation_text(
        platform: Platform,
        category: Category,
        request: RequestData,
        status: RequestStatus
):
    pl_label = PLATFORM_DETAILS[platform.value]['label']
    ct_label = CATEGORY_DETAILS[platform.value][category.value]['label']

    actual_status = REQUEST_STATUS_DETAILS[request.status.value]
    actual_status_icon = actual_status["icon"]
    actual_status_label = actual_status["label"]

    new_status = REQUEST_STATUS_DETAILS[status.value]
    new_status_icon = new_status["icon"]
    new_status_label = new_status["label"]

    text = (f"{_get_header()}\n\n"
            f"→ 📕 <i>Richieste Attive {pl_label} – {ct_label}</i>\n\n"
            "▪️ Da qui puoi gestire questa richiesta.\n\n")

    text += await get_request_details(request=request, admin=True)

    text += ("\n🔄 Stai <b>cambiando lo stato</b> di questa richiesta:\n\n"
             f"      {actual_status_icon} <i><b>{actual_status_label}</b></i>    ⟼"
             f"    {new_status_icon} <i><b>{new_status_label}</b></i>\n\n")

    if status is RequestStatus.COMPLETED:
        text += ("<blockquote>⚠️ <b>Attenzione</b> – Se confermi non potrai più cambiare lo stato della richiesta ed"
                 " essa verrà rimossa dalle richieste attive dopo 24 ore.</blockquote>\n\n")

    text += "🔹 <b>Confermi</b>?"

    return text


async def render_request_status_changed_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        ix: str,
        request: RequestData
):
    platform = request.get_platform()
    category = request.get_category()

    categories = get_platform_categories(platform=platform)
    if len(categories) > 1:
        back_button_callback_key = f"admin/manage_requests/active_requests/{platform.value}"
    else:
        back_button_callback_key = f"admin/manage_requests/active_requests"

    text = await _get_request_status_changed_text(
        platform=platform,
        category=category,
        request=request
    )

    keyboard = _get_admin_menage_request_keyboard(request=request, back_button_callback_key=back_button_callback_key)

    request_status_changed_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}",
            text=text,
            keyboard=keyboard
        )
    )

    await request_status_changed_panel.render(update=update, context=context)


async def _get_request_status_changed_text(
        platform: Platform,
        category: Category,
        request: RequestData
):
    pl_label = PLATFORM_DETAILS[platform.value]['label']
    ct_label = CATEGORY_DETAILS[platform.value][category.value]['label']

    status = REQUEST_STATUS_DETAILS[request.status.value]
    status_icon = status["icon"]
    status_label = status["label"]

    text = (f"{_get_header()}\n\n"
            f"→ 📕 <i>Richieste Attive {pl_label} – {ct_label}</i>\n\n"
            "▪️ Da qui puoi gestire questa richiesta.\n\n")

    text += await get_request_details(request=request, admin=True)

    if request.status is RequestStatus.COMPLETED:
        text += ("\n<blockquote>ℹ Lo stato di questa richiesta non può essere cambiato perché è stata già "
                 "contrassegnata come completata.</blockquote>\n")

    text += f"\n\n✅ <b>Stato {status_icon} <i>{status_label}</i> impostato</b>.\n"

    return text


async def render_admin_manage_request_remove_confirmation_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        ix: str,
        request: RequestData
):
    platform = request.get_platform()
    category = request.get_category()

    text = await _get_admin_manage_request_remove_confirmation_text(
        platform=platform,
        category=category,
        request=request
    )

    admin_manage_request_remove_confirmation_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}/remove",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="🗑 Rimuovi", callback_key="yes"),
                    ButtonItem(text="🔙 Annulla", callback_key=None)
                ]
            ]
        )
    )

    await admin_manage_request_remove_confirmation_panel.render(update=update, context=context)


async def _get_admin_manage_request_remove_confirmation_text(
        platform: Platform,
        category: Category,
        request: RequestData
):
    pl_label = PLATFORM_DETAILS[platform.value]['label']
    ct_label = CATEGORY_DETAILS[platform.value][category.value]['label']

    text = (f"{_get_header()}\n\n"
            f"→ 📕 <i>Richieste Attive {pl_label} – {ct_label}</i>\n\n"
            "▪️ Da qui puoi gestire questa richiesta.\n\n")

    text += await get_request_details(request=request, admin=True)

    text += "\n🚮 Confermi di <b>rimuovere questa richiesta non attiva</b>?"

    return text


async def render_admin_manage_request_removed_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        ix: str
):
    text = _get_admin_manage_request_removed_text()

    admin_manage_request_removed_panel = Panel(
        PanelConfig(
            base_path=update.callback_query.data.replace(f"/{ix}/remove/yes", ""),
            text=text,
            keyboard=[
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await admin_manage_request_removed_panel.render(update=update, context=context)


def _get_admin_manage_request_removed_text():
    text = ("🗑 <b>Richiesta inattiva rimossa correttamente</b>.\n\n"
            "<blockquote>ℹ L'utente che ha fatto tale richiesta potrà visualizzarla nell'archivio.</blockquote>")

    return text


def _get_header():
    return "❔ <b>Gestione Richieste</b>"
