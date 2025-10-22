from typing import Union

from telegram import Update
from telegram.constants import ChatAction

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import Request, CategorySetting
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS, REQUEST_STATUS_DETAILS, \
    Platform, Category, RequestStatus, RejectRequestReason, REQUEST_REJECTION_REASONS
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.request_utils import (get_requests_summary,
                                                        get_request_details,
                                                        get_platform_categories, get_last_n_requests)
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, create_and_render_panel
from aimods_bot.src.helpers.utils.time_utils import pluralize

log = logger.getChild("admin_requests_management_render")


async def render_admin_request_management_panel(update: Update, context: CustomContext):
    text = _get_admin_request_management_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="admin/manage_requests",
        text=text,
        keyboard=[
            [
                ButtonItem(text="⏯️ Gestione Sezioni", callback_key="manage_sections"),
                ButtonItem(text="⛔️ Gestisci Limitazioni", callback_key="manage_limitations")
            ],
            [
                ButtonItem(text="📘 Richieste Attive", callback_key="active_requests"),
                ButtonItem(text="📕 Archivio Richieste", callback_key="user_requests_archive")
            ],
            [ButtonItem(text="🔟 Ultime 10", callback_key="last_10")],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


def _get_admin_request_management_text():
    text = (f"{_get_header()}\n\n"
            "▪️ Da qui puoi gestire le richieste attive e settare le impostazioni per sui limiti delle richieste.\n\n"
            "🔹 Scegli un'opzione.")
    return text


async def render_admin_active_requests_management_panel(update: Update, context: CustomContext):
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

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="admin/manage_requests/active_requests",
        text=text,
        keyboard=keyboard
    )


def _get_admin_active_requests_management_text():
    text = (f"{_get_header()}\n\n"
            "→ 📕 <i>Richieste Attive</i>\n\n"
            "🔹 Scegli una piattaforma.")
    return text


async def render_admin_active_requests_category_selector_panel(
        update: Update,
        context: CustomContext,
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

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/active_requests/{platform.value}",
        text=text,
        keyboard=keyboard
    )


def _get_admin_active_requests_category_text(platform: Platform):
    text = (f"{_get_header()}\n\n"
            f"→ 📕 <i>Richieste Attive {PLATFORM_DETAILS[platform.value]['label']}</i>\n\n"
            "🔹 Scegli una categoria.")
    return text


async def render_admin_active_requests_category_panel(
        update: Update,
        context: CustomContext,
        platform: Platform,
        category: Category
):
    requests = context.get_active_category_requests(platform=platform, category=category)

    categories = get_platform_categories(platform=platform)
    if len(categories) > 1:
        back_button_callback_key = f"admin/manage_requests/active_requests/{platform.value}"
    else:
        back_button_callback_key = "admin/manage_requests/active_requests"

    if len(requests) == 1:
        ix = list(requests.values())[0].id
        request_data = context.get_active_request_by_id(ix=ix)

        return await render_admin_manage_request_panel(
            update=update,
            context=context,
            ix=ix,
            request=request_data,
            back_button_callback_key=back_button_callback_key
        )

    text = _get_active_requests_category_text(context=context, platform=platform, category=category, requests=requests)

    section_management_button = ButtonItem(
        text="⏯ Gestisci Sezione",
        callback_key=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}",
        override_path_generation=True
    )

    keyboard = [[section_management_button], []]
    for n, ix in enumerate(requests):
        request = requests[ix]
        if len(keyboard[-1]) == 2:
            keyboard.append([])
        keyboard[-1].append(ButtonItem(text=f"{n + 1}", callback_key=request.id))

    back_button = ButtonItem(
        text="🔙 Indietro",
        callback_key=back_button_callback_key,
        override_path_generation=(back_button_callback_key is not None)
    )

    keyboard.append([back_button]) if len(requests) else keyboard[-1].append(back_button)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/active_requests/{platform.value}/{category.value}",
        text=text,
        keyboard=keyboard
    )


def _get_active_requests_category_text(
        context: CustomContext,
        platform: Platform,
        category: Category,
        requests: dict[int, Request]
):
    config = getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)
    assert isinstance(config, CategorySetting)

    pl_label = PLATFORM_DETAILS[platform.value]['label']
    ct_label = CATEGORY_DETAILS[platform.value][category.value]['label']
    lenr = len(requests)

    text = (f"{_get_header()}\n\n"
            f"→ 📕 <i>Richieste Attive {pl_label} – {ct_label}</i>\n\n"
            f"👁‍🗨 Sezione – {f'🟢 Aperta (<i>{f'ancora {pluralize(
                config.limit - lenr,
                'richiesta',
                'richieste')
            }' if config.limit else '🆓 Nessun Limite'}</i>)' if config.toggle else '🔴 Chiusa'}\n\n")

    text += get_requests_summary(requests=requests)

    if lenr == 0:
        text += "ℹ️ Non ci sono richieste attive per questa categoria."
    else:
        text += "\n🔹 Scegli la richiesta da gestire."

    return text


async def render_admin_manage_request_panel(
        update: Update,
        context: CustomContext,
        ix: int,
        request: Request,
        back_button_callback_key: str = None
):
    platform = request.platform
    category = request.category

    text = await _get_admin_manage_request_text(request=request, platform=platform, category=category)
    keyboard = _get_admin_menage_request_keyboard(
        context=context,
        request=request,
        back_button_callback_key=back_button_callback_key
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}",
        text=text,
        keyboard=keyboard
    )


async def _get_admin_manage_request_text(
        request: Request,
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

    if status in (RequestStatus.COMPLETED, RequestStatus.REJECTED):
        text += ("\n<blockquote>ℹ Lo stato di questa richiesta non può essere cambiato perché è stata già "
                 f"contrassegnata come {'completata' if status == RequestStatus.COMPLETED else 'rifiutata'}."
                 f"</blockquote>\n")

    text += "\n🔹 Scegli un'opzione."

    return text


def _get_admin_menage_request_keyboard(context: CustomContext, request: Request, back_button_callback_key: str = None):
    steps = [None] + [el.value for el in RequestStatus] + [None]

    current_status = request.status
    current_status_value = current_status.value
    current_index = steps.index(str(current_status_value))
    next_status_button = steps[current_index + 1]
    previous_status_button = steps[current_index - 1]

    keyboard = [[]]
    if current_status not in (RequestStatus.COMPLETED, RequestStatus.REJECTED):
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
                ButtonItem(text="❌ Rifiuta Richiesta", callback_key="reject"),
                ButtonItem(text="🔄 Cambia Stato", callback_key="change_status")
            ]
        ])

    limit_buttons = [ButtonItem(text="⛔️ Limita Utente", callback_key=f"limit_{request.user_id}")]
    if context.get_user_request_limitations(user_id=request.user_id):
        limit_buttons.append(
            ButtonItem(
                text="🆓 Libera Utente",
                callback_key=f"admin/manage_requests/manage_limitations/remove_limitations/{request.user_id}",
                override_path_generation=True
            )
        )

    keyboard.extend([
        limit_buttons,
        [ButtonItem(
            text="🔙 Indietro",
            callback_key=back_button_callback_key,
            override_path_generation=(back_button_callback_key is not None)
        )]
    ])

    if current_status in (RequestStatus.COMPLETED, RequestStatus.REJECTED):
        keyboard[-2].insert(0, ButtonItem(
            text="🚮 Rimuovi da Attive", callback_key="remove"
        ))

    return keyboard


async def render_change_request_status_confirmation_panel(
        update: Update,
        context: CustomContext,
        ix: int,
        request: Request,
        status: RequestStatus
):
    platform = request.platform
    category = request.category

    text = await _get_render_change_request_status_confirmation_text(
        platform=platform,
        category=category,
        request=request,
        status=status
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}/{status.value}",
        text=text,
        keyboard=[
            [
                ButtonItem(text="✅ Conferma", callback_key="yes"),
                ButtonItem(text="🔙 Annulla", callback_key=None)
            ]
        ]
    )


async def _get_render_change_request_status_confirmation_text(
        platform: Platform,
        category: Category,
        request: Request,
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
        context: CustomContext,
        ix: int,
        request: Request
):
    platform = request.platform
    category = request.category

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

    keyboard = _get_admin_menage_request_keyboard(
        context=context,
        request=request,
        back_button_callback_key=back_button_callback_key
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}",
        text=text,
        keyboard=keyboard
    )


async def _get_request_status_changed_text(
        platform: Platform,
        category: Category,
        request: Request
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
        context: CustomContext,
        ix: int,
        request: Request
):
    platform = request.platform
    category = request.category

    text = await _get_admin_manage_request_remove_confirmation_text(
        platform=platform,
        category=category,
        request=request
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}/remove",
        text=text,
        keyboard=[
            [
                ButtonItem(text="🗑 Rimuovi", callback_key="yes"),
                ButtonItem(text="🔙 Annulla", callback_key=None)
            ]
        ]
    )


async def _get_admin_manage_request_remove_confirmation_text(
        platform: Platform,
        category: Category,
        request: Request
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
        context: CustomContext,
        ix: int
):
    text = _get_admin_manage_request_removed_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=update.callback_query.data.replace(f"/{ix}/remove/yes", ""),
        text=text,
        keyboard=[
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


def _get_admin_manage_request_removed_text():
    text = ("🗑 <b>Richiesta Inattiva Rimossa Correttamente</b>.\n\n"
            "<blockquote>ℹ L'utente che ha fatto tale richiesta potrà visualizzarla nell'archivio.</blockquote>")
    return text


def _get_header():
    return "❔ <b>Gestione Richieste</b>"


async def render_admin_manage_request_change_status_panel(
        update: Update,
        context: CustomContext,
        ix: int,
        request: Request
):
    text = await _get_admin_manage_request_change_status_text(request=request)

    platform = request.platform
    category = request.category

    path = f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}"

    keyboard = [[]]
    for sk in REQUEST_STATUS_DETAILS:
        if sk == "cancelled":
            continue
        status = REQUEST_STATUS_DETAILS[sk]
        if len(keyboard[-1]) >= 2:
            keyboard.append([])
        if sk == "rejected":
            ckey = "reject"
            override = False
        elif request.status.value != sk:
            ckey = sk
            override = False
        else:
            ckey = f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}"
            override = True
        keyboard[-1].append(ButtonItem(
            text=f"{status['icon']} {status['label']}",
            callback_key=ckey,
            override_path_generation=override
        ))

    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=path, override_path_generation=True)])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=path,
        text=text,
        keyboard=keyboard
    )


async def _get_admin_manage_request_change_status_text(request: Request):
    text = (f"{_get_header()}\n\n"
            f"→ 🔄 <i>Cambio Stato Richiesta</i>\n\n"
            "▪️ Da qui puoi gestire questa richiesta.\n\n")

    text += await get_request_details(request=request, admin=True)

    text += "\n🔹 Scegli il nuovo stato da impostare."

    return text


async def render_admin_reject_request_panel(
        update: Update,
        context: CustomContext,
        ix: int,
        request: Request
):
    text = await _get_admin_reject_request_text(request=request)

    platform = request.platform
    category = request.category

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}/reject",
        text=text,
        keyboard=[
            [ButtonItem(text="Serverside", callback_key=RejectRequestReason.SERVERSIDE.value)],
            [ButtonItem(text="Non disponibile al momento", callback_key=RejectRequestReason.NOT_AVAILABLE.value)],
            [ButtonItem(text="Già disponibile", callback_key=RejectRequestReason.ALREADY_AVAILABLE.value)],
            [ButtonItem(text="Richiesta non chiara", callback_key=RejectRequestReason.UNCLEAR.value)],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


async def _get_admin_reject_request_text(request: Request):
    text = (f"{_get_header()}\n\n"
            f"→ ❌ <i>Rifiuto Richiesta</i>\n\n"
            "▪️ Da qui puoi gestire questa richiesta.\n\n")

    text += await get_request_details(request=request, admin=True)

    text += "\n❓ Scegli il motivo del rifiuto o scrivine uno."

    return text


async def render_admin_confirm_rejection_panel(
        update: Update,
        context: CustomContext,
        ix: int,
        request: Request,
        reason: Union[RejectRequestReason, str]
):
    text = await _get_admin_confirm_rejection_text(request=request, rejection_reason=reason)
    message_id = context.pydc.persistent.bot_message_id
    context.pydc.persistent.bot_message_id = None

    platform = request.platform
    category = request.category

    base_path = f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}/reject/{reason}"

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="✅ Conferma", callback_key="yes"),
                ButtonItem(text="🔙 Indietro", callback_key=None)
            ]
        ],
        message_id=message_id
    )


async def _get_admin_confirm_rejection_text(request: Request, rejection_reason: Union[RejectRequestReason, str]):
    text = (f"{_get_header()}\n\n"
            f"→ ❌ <i>Rifiuto Richiesta</i>\n\n"
            "▪️ Da qui puoi gestire questa richiesta.\n\n")

    text += await get_request_details(request=request, admin=True)

    if rejection_reason in REQUEST_REJECTION_REASONS:
        rejection_reason = REQUEST_REJECTION_REASONS[rejection_reason]

    text += ("\n\n<b>❗ Stai rifiutando questa richiesta per il seguente motivo:\n\n"
             f"      ↪ <i>{rejection_reason}</i></b>\n\n"
             "<blockquote>⚠️ <b>Attenzione</b> – Se confermi non potrai più cambiare lo stato della richiesta ed"
             " essa verrà rimossa dalle richieste attive dopo 24 ore.</blockquote>\n\n"
             "🔹 <b>Confermi?</b>")

    return text


async def render_admin_rejection_confirmed_panel(
        update: Update,
        context: CustomContext,
        ix: int,
        request: Request,
        reason: str
):
    platform = request.platform
    category = request.category

    text = _get_admin_rejection_confirmed_text(ix=ix, reason=reason)
    base_path = f"admin/manage_requests/active_requests/{platform.value}/{category.value}/{ix}/reject/{reason}/yes"

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="🔙 Indietro",
                    callback_key="admin/manage_requests/active_requests",
                    override_path_generation=True
                ),
                ButtonItem(
                    text="🏠 Home",
                    callback_key="admin",
                    override_path_generation=True
                )
            ]
        ]
    )


def _get_admin_rejection_confirmed_text(ix: int, reason: str):
    if reason in REQUEST_REJECTION_REASONS:
        reason = REQUEST_REJECTION_REASONS[reason]

    text = ("❌ <b>Richiesta Rifiutata Correttamente</b>\n\n"
            f"      🔸 <u>ID</u> – <code>{ix}</code>\n"
            f"      🔸 <u>Motivazione</u> – <i>{reason}</i>\n\n"
            "🔹 Scegli un'opzione.")

    return text


async def render_admin_user_requests_archive_panel(update: Update, context: CustomContext):
    context.pydc.persistent.bot_message_id = update.effective_message.message_id

    text = _get_admin_user_requests_archive_()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="admin/manage_requests/user_requests_archive",
        text=text,
        keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=None)]]
    )


def _get_admin_user_requests_archive_():
    text = ("📕 <b>Archivio Richieste Utente</b>\n\n"
            "▫ Da qui puoi visionare l'archivio delle richieste di un utente.\n\n"
            "🔹 Fornisci un ID o uno username.")
    return text


async def send_user_request_status_changed_notification(
        update: Update,
        context: CustomContext,
        user_id: int,
        request: Request
):
    text = _get_user_request_status_changed_notification_text(request=request)
    ix = request.id

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="user",
        text=text,
        keyboard=[
            [
                ButtonItem(text="🚮 Chiudi", callback_key="close_menu"),
                ButtonItem(
                    text="👁 Visiona Richiesta",
                    callback_key=f"user/view_requests/active_requests/details/{ix}",
                    override_path_generation=True
                )
            ]
        ],
        user_id=user_id
    )


def _get_user_request_status_changed_notification_text(request: Request):
    pl, ca = request.platform.value, request.category.value
    pl_label = PLATFORM_DETAILS[pl]["label"]
    ca_label = CATEGORY_DETAILS[pl][ca]["label"]

    text = (f"🆙 <b>Aggiornamento Richiesta <code>{request.id}</code></b>\n\n"
            f"▫ La tua richiesta (<b>{ca_label} {pl_label}</b>) ha appena ricevuto il suo <b>esito</b>!")

    return text


async def render_last_ten_requests_platform_panel(update: Update, context: CustomContext):
    text = _get_last_ten_requests_platform_text()

    keyboard = [[]]
    for pl in PLATFORM_DETAILS:
        item = PLATFORM_DETAILS[pl]
        if len(keyboard[-1]) >= 2:
            keyboard.append([])
        keyboard[-1].append(ButtonItem(text=f"{item['icon']} {item['label']}", callback_key=pl))
    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=None)])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="admin/manage_requests/last_10",
        text=text,
        keyboard=keyboard
    )


def _get_last_ten_requests_platform_text():
    text = _get_header() + "\n\n      → 🔟 <i>Ultime 10 Richieste</i>\n\n"

    text += ("▫ Da qui puoi visionare le ultima 10 richieste per categoria.\n\n"
             "🔹 Scegli una piattaforma.")

    return text


async def render_last_ten_requests_category_panel(update: Update, context: CustomContext, pl: Platform):
    cats = get_platform_categories(pl)
    if len(cats) == 1:
        return await render_last_ten_requests_section_panel(update=update, context=context, pl=pl, ca=list(cats)[0])

    text = _get_last_ten_requests_category_text(pl=pl)

    keyboard = [[]]
    for ca in CATEGORY_DETAILS[pl.value]:
        item = CATEGORY_DETAILS[pl.value][ca]
        if len(keyboard[-1]) >= 2:
            keyboard.append([])
        keyboard[-1].append(ButtonItem(text=f"{item['icon']} {item['label']}", callback_key=ca))
    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=None)])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/last_10/{pl.value}",
        text=text,
        keyboard=keyboard
    )


def _get_last_ten_requests_category_text(pl: Platform):
    item = PLATFORM_DETAILS[pl.value]
    text = _get_header() + f"\n\n      → 🔟 <i>Ultime 10 Richieste</i> – {item['icon']} {item['label']}\n\n"

    text += ("▫ Da qui puoi visionare le ultima 10 richieste per categoria.\n\n"
             "🔹 Scegli una categoria.")

    return text


async def render_last_ten_requests_section_panel(update: Update, context: CustomContext, pl: Platform, ca: Category):
    await context.bot.send_chat_action(
        chat_id=update.effective_message.chat_id,
        action=ChatAction.TYPING
    )
    requests = await get_last_n_requests(n=10, pl=pl, ca=ca)
    text = await _get_last_ten_requests_section_text(requests=requests, pl=pl, ca=ca)

    if len(get_platform_categories(pl)) == 1:
        back_button_callback_data = "admin/manage_requests/last_10"
    else:
        back_button_callback_data = f"admin/manage_requests/last_10/{pl.value}"

    await safe_delete(update=update, context=context)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/last_10/{pl.value}/{ca.value}",
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="📕 Archivio Richieste",
                    callback_key="admin/manage_requests/user_requests_archive",
                    override_path_generation=True
                )
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=back_button_callback_data, override_path_generation=True)]
        ],
        send=True
    )


async def _get_last_ten_requests_section_text(requests: list[Request], pl: Platform, ca: Category) -> str:
    pl_icon = PLATFORM_DETAILS[pl.value]["icon"]
    ca_label = CATEGORY_DETAILS[pl.value][ca.value]["label"]
    text = _get_header() + f"\n\n      → 🔟 <i>Ultime 10 Richieste</i> – {pl_icon} {ca_label}\n\n"
    if len(requests) == 0:
        text += ("<blockquote>ℹ Nessuna richiesta ancora formulata per questa sezione.</blockquote>\n\n"
                 "🔹 Scegli un'opzione.")
    else:
        text += get_requests_summary(requests={request.id: request for request in requests}, with_authors=True)
        text += ("\n<blockquote>🔍 <b>Maggiori Informazioni</b> – Visiona l'archivio di un utente per maggiori "
                 "informazioni su una richiesta, o contatta Layton.</blockquote>\n\n"
                 "🔹 Scegli un'opzione.")

    return text
