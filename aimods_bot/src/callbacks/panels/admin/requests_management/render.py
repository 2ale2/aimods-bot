from typing import Union

from telegram import Update
from telegram.constants import ChatAction

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import Request, CategorySetting
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS, REQUEST_STATUS_DETAILS, \
    Platform, Category, RequestStatus, RejectRequestReason, REQUEST_REJECTION_REASONS
from aimods_bot.src.helpers.constants.conversation_paths.navigation import AdminRequestManagementRoute, AdminRoute, \
    AdminRequestsRoute, AdminRequestsLimitationsRoute, GlobalAction, UserRoute, UserManageRequestsRoute, \
    AdminManageRequestLimitationsUtils
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.request_utils import (get_requests_summary,
                                                        get_request_details,
                                                        get_platform_categories, get_last_n_requests)
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, create_and_render_panel, chunk_buttons
from aimods_bot.src.helpers.utils.time_utils import pluralize

log = logger.getChild("admin_requests_management_render")


def _get_header():
    return "❔ <b>Gestione Richieste</b>"


async def render_admin_request_management_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _get_admin_request_management_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="⏯️ Gestione Sezioni",
                    callback_key=base_path.add(AdminRequestsRoute.MANAGE_SECTIONS)
                ),
                ButtonItem(
                    text="⛔️ Gestisci Limitazioni",
                    callback_key=base_path.add(AdminRequestsRoute.MANAGE_LIMITATIONS)
                )
            ],
            [
                ButtonItem(
                    text="📘 Richieste Attive",
                    callback_key=base_path.add(AdminRequestsRoute.ACTIVE)
                ),
                ButtonItem(
                    text="📕 Archivio Richieste",
                    callback_key=base_path.add(AdminRequestsRoute.USER_REQUESTS_ARCHIVE)
                )
            ],
            [
                ButtonItem(
                    text="🔟 Ultime 10",
                    callback_key=base_path.add(AdminRequestsRoute.LAST_10)
                )
            ],
            [
                ButtonItem(
                    text="🔙 Indietro",
                    callback_key=base_path.back()
                )
            ]
        ]
    )


def _get_admin_request_management_text():
    text = (f"{_get_header()}\n\n"
            "▪️ Da qui puoi gestire le richieste attive e settare le impostazioni per sui limiti delle richieste.\n\n"
            "🔹 Scegli un'opzione.")
    return text


async def render_admin_active_requests_management_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _get_admin_request_management_text()

    buttons = [
        ButtonItem(text=f"{d['icon']} {d['label']}", callback_key=base_path.add(key))
        for key, d in PLATFORM_DETAILS.items()
    ]

    keyboard = chunk_buttons(buttons=buttons, size=2)
    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


def _get_admin_active_requests_management_text():
    return (
        f"{_get_header()}\n\n"
        "→ 📕 <i>Richieste Attive</i>\n\n"
        "🔹 Scegli una piattaforma."
    )


async def render_admin_active_requests_category_selector_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
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
            base_path=base_path,
            platform=platform,
            category=category
        )

    buttons = [
        ButtonItem(text=f"{d['icon']} {d['label']}", callback_key=base_path.add(key))
        for key, d in categories.items()
    ]

    keyboard = chunk_buttons(buttons=buttons, size=2)
    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


def _get_admin_active_requests_category_text(platform: Platform):
    return (
        f"{_get_header()}\n\n"
        f"→ 📕 <i>Richieste Attive {PLATFORM_DETAILS[platform.value]['label']}</i>\n\n"
        "🔹 Scegli una categoria."
    )


async def render_admin_active_requests_category_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        platform: Platform,
        category: Category
):
    requests = context.get_active_category_requests(platform=platform, category=category)

    categories = get_platform_categories(platform=platform)
    if len(categories) > 1:
        back_button_callback_key = base_path.back()
    else:
        back_button_callback_key = base_path.back(2)

    if len(requests) == 1:
        ix = list(requests.values())[0].id
        request_data = context.get_active_request_by_id(ix=ix)

        return await render_admin_manage_request_panel(
            update=update,
            context=context,
            request=request_data,
            base_path=base_path
        )

    text = _get_active_requests_category_text(context=context, platform=platform, category=category, requests=requests)

    keyboard = [[
        ButtonItem(
            text="⏯ Gestisci Sezione",
            callback_key=PathBuilder(
                AdminRoute.ROOT,
                AdminRoute.MANAGE_REQUESTS,
                AdminRequestsRoute.MANAGE_SECTIONS,
                platform.value,
                category.value
            )
        )
    ]]

    req_buttons = [
        ButtonItem(
            text=f"{i + 1}",
            callback_key=base_path.add(req.id)) for i, req in enumerate(requests.values())
    ]
    keyboard.extend(chunk_buttons(req_buttons, 2))

    back_button = ButtonItem(
        text="🔙 Indietro",
        callback_key=back_button_callback_key
    )

    keyboard.append([back_button]) if len(requests) else keyboard[-1].append(back_button)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
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

    if lenr == 0:
        text += "ℹ️ Non ci sono richieste attive per questa categoria."
    else:
        text += get_requests_summary(requests=requests)
        text += "\n🔹 Scegli la richiesta da gestire."

    return text


async def render_admin_manage_request_panel(
        update: Update,
        context: CustomContext,
        request: Request,
        base_path: PathBuilder
):
    platform = request.platform
    category = request.category

    text = await _get_admin_manage_request_text(request=request, platform=platform, category=category)
    keyboard = _get_admin_menage_request_keyboard(
        context=context,
        request=request,
        base_path=base_path,
        back_callback_key=base_path.back()
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
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


def _get_admin_menage_request_keyboard(
        context: CustomContext,
        request: Request,
        base_path: PathBuilder,
        back_callback_key: PathBuilder
):
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
                callback_key=base_path.add(next_status_button))
            )
        if previous_status_button:
            previous_status_icon = REQUEST_STATUS_DETAILS[previous_status_button]["icon"]
            previous_status_label = REQUEST_STATUS_DETAILS[previous_status_button]["label"]
            keyboard[0].insert(0, ButtonItem(
                text=f"{previous_status_icon} {previous_status_label}",
                callback_key=base_path.add(previous_status_button))
            )

        keyboard.extend([
            [
                ButtonItem(
                    text="❌ Rifiuta Richiesta",
                    callback_key=base_path.add(AdminRequestManagementRoute.REJECT)
                ),
                ButtonItem(
                    text="🔄 Cambia Stato",
                    callback_key=base_path.add(AdminRequestManagementRoute.CHANGE_STATUS)
                )
            ]
        ])

    limit_buttons = [ButtonItem(
        text="⛔️ Limita Utente",
        callback_key=base_path.add(AdminManageRequestLimitationsUtils.LIMIT, str(request.user_id)))
    ]
    if context.get_user_request_limitations(user_id=request.user_id):
        limit_buttons.append(
            ButtonItem(
                text="🆓 Libera Utente",
                callback_key=PathBuilder(
                    AdminRoute.ROOT,
                    AdminRoute.MANAGE_REQUESTS,
                    AdminRequestsRoute.MANAGE_LIMITATIONS,
                    AdminRequestsLimitationsRoute.REMOVE_LIMITATIONS,
                    str(request.user_id)
                )
            )
        )

    keyboard.extend([limit_buttons, [ButtonItem(text="🔙 Indietro", callback_key=back_callback_key)]])

    if current_status in (RequestStatus.COMPLETED, RequestStatus.REJECTED):
        keyboard[-2].insert(0, ButtonItem(
            text="🚮 Rimuovi da Attive", callback_key=base_path.add(AdminRequestManagementRoute.REMOVE)
        ))

    return keyboard


async def render_change_request_status_confirmation_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
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
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="✅ Conferma", callback_key=base_path.add(GlobalAction.YES)),
                ButtonItem(text="🔙 Annulla", callback_key=base_path.back())
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
        base_path: PathBuilder,
        request: Request
):
    platform = request.platform
    category = request.category

    categories = get_platform_categories(platform=platform)
    if len(categories) > 1:
        back_callback_key = base_path.back()
    else:
        back_callback_key = base_path.back(2)

    text = await _get_request_status_changed_text(
        platform=platform,
        category=category,
        request=request
    )

    keyboard = _get_admin_menage_request_keyboard(
        context=context,
        request=request,
        base_path=base_path,
        back_callback_key=back_callback_key
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
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
        base_path: PathBuilder,
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
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="🗑 Rimuovi", callback_key=base_path.add(GlobalAction.YES)),
                ButtonItem(text="🔙 Annulla", callback_key=base_path.back())
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
        base_path: PathBuilder
):
    text = _get_admin_manage_request_removed_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [ButtonItem(text="🔙 Indietro", callback_key=base_path)]
        ]
    )


def _get_admin_manage_request_removed_text():
    text = ("🗑 <b>Richiesta Inattiva Rimossa Correttamente</b>.\n\n"
            "<blockquote>ℹ L'utente che ha fatto tale richiesta potrà visualizzarla nell'archivio.</blockquote>")
    return text


async def render_admin_manage_request_change_status_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        request: Request
):
    text = await _get_admin_manage_request_change_status_text(request=request)

    keyboard = [[]]
    for sk in REQUEST_STATUS_DETAILS:
        if sk == "cancelled":
            continue
        status = REQUEST_STATUS_DETAILS[sk]
        if len(keyboard[-1]) >= 2:
            keyboard.append([])
        if sk == "rejected":
            ckey = "reject"
        elif request.status.value != sk:
            ckey = sk
        else:
            ckey = base_path.back()
        keyboard[-1].append(ButtonItem(
            text=f"{status['icon']} {status['label']}",
            callback_key=base_path.add(ckey)
        ))

    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
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
        base_path: PathBuilder,
        request: Request
):
    text = await _get_admin_reject_request_text(request=request)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="Serverside",
                    callback_key=base_path.add(RejectRequestReason.SERVERSIDE.value)
                )
            ],
            [
                ButtonItem(
                    text="Non disponibile al momento",
                    callback_key=base_path.add(RejectRequestReason.NOT_AVAILABLE.value)
                )
            ],
            [
                ButtonItem(
                    text="Già disponibile",
                    callback_key=base_path.add(RejectRequestReason.ALREADY_AVAILABLE.value)
                )
            ],
            [
                ButtonItem(
                    text="Richiesta non chiara",
                    callback_key=base_path.add(RejectRequestReason.UNCLEAR.value)
                )
            ],
            [
                ButtonItem(
                    text="🔙 Indietro",
                    callback_key=base_path.back())]
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
        base_path: PathBuilder,
        request: Request,
        reason: Union[RejectRequestReason, str]
):
    text = await _get_admin_confirm_rejection_text(request=request, rejection_reason=reason)
    message_id = context.pydc.persistent.bot_message_id
    context.pydc.persistent.bot_message_id = None

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="✅ Conferma", callback_key=base_path.add(GlobalAction.YES)),
                ButtonItem(text="🔙 Indietro", callback_key=base_path.back())
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
        base_path: PathBuilder,
        ix: int,
        reason: str
):
    text = _get_admin_rejection_confirmed_text(ix=ix, reason=reason)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="🔙 Indietro",
                    callback_key=PathBuilder(
                        AdminRoute.ROOT,
                        AdminRoute.MANAGE_REQUESTS,
                        AdminRequestsRoute.ACTIVE
                    )
                ),
                ButtonItem(text="🏠 Home", callback_key=PathBuilder(AdminRoute.ROOT))
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


async def render_admin_user_requests_archive_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    context.pydc.persistent.bot_message_id = update.effective_message.message_id

    text = _get_admin_user_requests_archive()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]]
    )


def _get_admin_user_requests_archive():
    return (
        "📕 <b>Archivio Richieste Utente</b>\n\n"
        "▫ Da qui puoi visionare l'archivio delle richieste di un utente.\n\n"
        "🔹 Fornisci un ID o uno username."
    )


async def send_user_request_status_changed_notification(
        update: Update,
        context: CustomContext,
        user_id: int,
        request: Request
):
    text = _get_user_request_status_changed_notification_text(request=request)
    ix = request.id

    base_path = PathBuilder(UserRoute.ROOT)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="🚮 Chiudi", callback_key=PathBuilder(GlobalAction.CLOSE_MENU)),
                ButtonItem(
                    text="👁 Visiona Richiesta",
                    callback_key=base_path.add(
                        UserRoute.VIEW_REQUESTS,
                        UserManageRequestsRoute.ACTIVE,
                        UserManageRequestsRoute.DETAILS,
                        ix
                    )
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


async def render_last_ten_requests_platform_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _get_last_ten_requests_platform_text()

    buttons = [
        ButtonItem(text=f"{d['icon']} {d['label']}", callback_key=base_path.add(key))
        for key, d in PLATFORM_DETAILS.items()
    ]
    keyboard = chunk_buttons(buttons, 2)
    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


def _get_last_ten_requests_platform_text():
    text = _get_header() + "\n\n      → 🔟 <i>Ultime 10 Richieste</i>\n\n"

    text += ("▫ Da qui puoi visionare le ultima 10 richieste per categoria.\n\n"
             "🔹 Scegli una piattaforma.")

    return text


async def render_last_ten_requests_category_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        pl: Platform
):
    cats = get_platform_categories(pl)
    if len(cats) == 1:
        return await render_last_ten_requests_section_panel(
            update=update,
            context=context,
            platform=pl,
            category=list(cats)[0],
            base_path=base_path
        )

    text = _get_last_ten_requests_category_text(pl=pl)

    buttons = [
        ButtonItem(text=f"{d['icon']} {d['label']}", callback_key=base_path.add(key))
        for key, d in CATEGORY_DETAILS[pl.value].items()
    ]
    keyboard = chunk_buttons(buttons, 2)
    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


def _get_last_ten_requests_category_text(pl: Platform):
    item = PLATFORM_DETAILS[pl.value]
    text = _get_header() + f"\n\n      → 🔟 <i>Ultime 10 Richieste</i> – {item['icon']} {item['label']}\n\n"

    text += ("▫ Da qui puoi visionare le ultima 10 richieste per categoria.\n\n"
             "🔹 Scegli una categoria.")

    return text


async def render_last_ten_requests_section_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        platform: Platform,
        category: Category
):
    await context.bot.send_chat_action(
        chat_id=update.effective_message.chat_id,
        action=ChatAction.TYPING
    )
    requests = await get_last_n_requests(n=10, pl=platform, ca=category)
    text = await _get_last_ten_requests_section_text(requests=requests, pl=platform, ca=category)

    if len(get_platform_categories(platform)) > 1:
        back_button_callback_data = base_path.back()
    else:
        back_button_callback_data = base_path.back(2)

    await safe_delete(update=update, context=context)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="📕 Archivio Richieste",
                    callback_key=PathBuilder(
                        AdminRoute.ROOT,
                        AdminRoute.MANAGE_REQUESTS,
                        AdminRequestsRoute.USER_REQUESTS_ARCHIVE
                    )
                )
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=back_button_callback_data)]
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
