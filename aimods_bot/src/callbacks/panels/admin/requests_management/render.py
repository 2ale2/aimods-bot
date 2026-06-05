from telegram import Update
from telegram.constants import ChatAction

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.constants import Platform, RequestStatus, RejectRequestReason
from aimods_bot.src.helpers.constants.path_navigation import AdminRequestManagementRoute, AdminRoute, \
    AdminRequestsRoute, LimitationsAction, GlobalAction, UserRoute, UserManageRequestsRoute, \
    LimitationsOp
from aimods_bot.src.helpers.models.requests import PLATFORM_CATEGORY_REGISTRY, BaseRequest
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.request_utils import get_requests_summary, get_request_details, get_last_n_requests
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, create_and_render_panel, chunk_buttons
from aimods_bot.src.helpers.utils.time_utils import pluralize

log = logger.getChild(__name__)


def _get_header():
    return "❔ <b>Gestione Richieste</b>"


async def _build_request_panel_preamble(
    request: BaseRequest,
    icon: str,
    title: str,
    *,
    include_platform_category: bool = True,
    body: str = "▪️ Da qui puoi gestire questa richiesta.\n\n",
    include_details: bool = True,
) -> str:
    if include_platform_category:
        ca_label = PLATFORM_CATEGORY_REGISTRY[request.section.platform][request.section.category].label
        subtitle = f"{title} {request.section.platform.label} – {ca_label}"
    else:
        subtitle = title

    text = (
        f"{_get_header()}\n\n"
        f"→ {icon} <i>{subtitle}</i>\n\n"
        f"{body}"
    )
    if include_details:
        text += get_request_details(request=request, admin=True)
    return text


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
        ButtonItem(text=f"{pl.icon} {pl.label}", callback_key=base_path.add(pl))
        for pl in Platform
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

    categories = PLATFORM_CATEGORY_REGISTRY.get(platform, None)
    if not categories:
        raise ValueError(f"Platform {platform.value} not recognized!")

    if len(categories) == 1:
        category = next(iter(categories))

        return await render_admin_active_requests_category_panel(
            update=update,
            context=context,
            base_path=base_path,
            section=RequestSection(platform=platform, category=category)
        )

    buttons = [
        ButtonItem(text=f"{cat_config.icon} {cat_config.label}", callback_key=base_path.add(cat_key))
        for cat_key, cat_config in categories.items()
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
        f"→ 📕 <i>Richieste Attive {platform.label}</i>\n\n"
        "🔹 Scegli una categoria."
    )


async def render_admin_active_requests_category_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        section: RequestSection
):
    requests = context.get_active_category_requests(section=section)

    categories = PLATFORM_CATEGORY_REGISTRY.get(section.platform)
    if not categories:
        raise ValueError(f"Platform {section.platform.value} not recognized!")

    if len(categories) > 1:
        back_button_callback_key = base_path.back()
    else:
        back_button_callback_key = base_path.back(2)

    if len(requests) == 1:
        ix = next(iter(requests))
        request_data = context.get_active_request_by_id(ix=ix)

        return await render_admin_manage_request_panel(
            update=update,
            context=context,
            request=request_data,
            base_path=base_path
        )

    text = _get_active_requests_category_text(context=context, section=section, requests=requests)

    keyboard = [[
        ButtonItem(
            text="⏯ Gestisci Sezione",
            callback_key=PathBuilder(
                AdminRoute.ROOT,
                AdminRoute.MANAGE_REQUESTS,
                AdminRequestsRoute.MANAGE_SECTIONS,
                section.platform,
                section.category
            )
        )
    ]]

    req_buttons = [
        ButtonItem(
            text=f"{i}",
            callback_key=base_path.add(str(req))) for i, req in enumerate(requests.keys(), start=1)
    ]
    keyboard.extend(chunk_buttons(req_buttons, 2))

    back_button = ButtonItem(
        text="🔙 Indietro",
        callback_key=back_button_callback_key
    )

    if len(requests):
        keyboard.append([back_button])
    else:
        keyboard[-1].append(back_button)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


def _get_active_requests_category_text(
        context: CustomContext,
        section: RequestSection,
        requests: dict[int, BaseRequest]
):
    request_settings = context.pydb.configuration.settings.request
    platform_key = section.platform.value
    category_key = section.category.value

    config = getattr(getattr(request_settings, platform_key), category_key)
    assert isinstance(config, CategorySetting)

    lenr = len(requests)

    text = (f"{_get_header()}\n\n"
            f"→ 📕 <i>Richieste Attive {section.platform.label} – {section.category_config.label}</i>\n\n"
            f"👁‍🗨 Sezione – {f'🟢 Aperta (<i>{f'ancora {pluralize(
                config.limit - lenr,
                'richiesta',
                'richieste')
            }' if config.limit else '🆓 Nessun Limite'}</i>)' if config.toggle else '🔴 Chiusa'}\n\n")

    if lenr == 0:
        text += "ℹ️ Non ci sono richieste attive per questa categoria."
    else:
        text += get_requests_summary(requests=list(requests.values()))
        text += "\n🔹 Scegli la richiesta da gestire."

    return text


async def render_admin_manage_request_panel(
        update: Update,
        context: CustomContext,
        request: BaseRequest,
        base_path: PathBuilder
):
    platform = request.platform
    category = request.category

    if not platform or not category:
        raise ValueError("Platform and category must not be None!")

    text = await _get_admin_manage_request_text(request=request)
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


async def _get_admin_manage_request_text(request: BaseRequest) -> str:
    text = await _build_request_panel_preamble(request, "📕", "Richieste Attive")
    if request.status in (RequestStatus.COMPLETED, RequestStatus.REJECTED):
        text += ("\n<blockquote>ℹ Lo stato di questa richiesta non può essere cambiato perché è stata già "
                 f"contrassegnata come {request.status.label.lower()}.</blockquote>\n")
    text += "\n🔹 Scegli un'opzione."
    return text


def _get_admin_menage_request_keyboard(
        context: CustomContext,
        request: BaseRequest,
        base_path: PathBuilder,
        back_callback_key: PathBuilder
):
    steps = [None] + [el for el in RequestStatus] + [None]

    current_status = request.status
    current_index = steps.index(current_status)
    next_status_button = steps[current_index + 1]
    previous_status_button = steps[current_index - 1]

    keyboard = [[]]
    if current_status not in (RequestStatus.COMPLETED, RequestStatus.REJECTED):
        if next_status_button:
            keyboard[0].insert(0, ButtonItem(
                text=f"{next_status_button.icon} {next_status_button.label}",
                callback_key=base_path.add(next_status_button))
            )
        if previous_status_button:
            keyboard[0].insert(0, ButtonItem(
                text=f"{previous_status_button.icon} {previous_status_button.label}",
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
        callback_key=base_path.add(LimitationsOp.LIMIT, str(request.user_id)))
    ]
    if context.get_user_request_limitations(user_id=request.user_id):
        limit_buttons.append(
            ButtonItem(
                text="🆓 Libera Utente",
                callback_key=PathBuilder(
                    AdminRoute.ROOT,
                    AdminRoute.MANAGE_REQUESTS,
                    AdminRequestsRoute.MANAGE_LIMITATIONS,
                    LimitationsAction.REMOVE_LIMITATIONS,
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
        request: BaseRequest,
        status: RequestStatus
):
    platform = request.platform
    category = request.category

    if not platform or not category:
        raise ValueError("Platform and category must not be None!")

    text = await _get_render_change_request_status_confirmation_text(request=request, status=status)

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


async def _get_render_change_request_status_confirmation_text(request: BaseRequest, status: RequestStatus):
    text = await _build_request_panel_preamble(request, "📕", "Richieste Attive")
    text += ("\n🔄 Stai <b>cambiando lo stato</b> di questa richiesta:\n\n"
             f"      {request.status.icon} <i><b>{request.status.label}</b></i>    ⟼"
             f"    {status.icon} <i><b>{status.label}</b></i>\n\n")
    if status is RequestStatus.COMPLETED:
        text += ("<blockquote>⚠️ <b>Attenzione</b> – Se confermi non potrai più cambiare lo stato della richiesta ed"
                 " essa verrà rimossa dalle richieste attive dopo 24 ore.</blockquote>\n\n")
    text += "🔹 <b>Confermi</b>?"
    return text


async def render_request_status_changed_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        request: BaseRequest
):
    platform = request.platform
    category = request.category

    if not platform or not category:
        raise ValueError("Platform and category must not be None!")

    categories = PLATFORM_CATEGORY_REGISTRY.get(platform)

    if not categories:
        raise ValueError(f"Platform {platform.value} not supported!")

    if len(categories) > 1:
        back_callback_key = base_path.back()
    else:
        back_callback_key = base_path.back(2)

    text = await _get_request_status_changed_text(request=request)

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


async def _get_request_status_changed_text(request: BaseRequest) -> str:
    text = await _build_request_panel_preamble(request, "📕", "Richieste Attive")

    if not request.status:
        raise ValueError("Request status must not be None!")

    if request.status is RequestStatus.COMPLETED:
        text += ("\n<blockquote>ℹ Lo stato di questa richiesta non può essere cambiato perché è stata già "
                 "contrassegnata come completata.</blockquote>\n")
    text += f"\n\n✅ <b>Stato {request.status.icon} <i>{request.status.label}</i> impostato</b>.\n"
    return text


async def render_admin_manage_request_remove_confirmation_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        request: BaseRequest
):
    platform = request.platform
    category = request.category

    if not platform or not category:
        raise ValueError("Platform and category must not be None!")

    text = await _get_admin_manage_request_remove_confirmation_text(request=request)

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


async def _get_admin_manage_request_remove_confirmation_text(request: BaseRequest) -> str:
    text = await _build_request_panel_preamble(request, "📕", "Richieste Attive")
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
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
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
        request: BaseRequest
):
    text = await _get_admin_manage_request_change_status_text(request=request)

    keyboard = [[]]
    for sk in RequestStatus:
        if sk == RequestStatus.CANCELLED:
            continue
        if len(keyboard[-1]) >= 2:
            keyboard.append([])
        if sk == RequestStatus.REJECTED:
            button_base_path = base_path.add(AdminRequestManagementRoute.REJECT)
        elif request.status != sk:
            button_base_path = base_path.add(sk)
        else:
            button_base_path = base_path.back()
        keyboard[-1].append(ButtonItem(text=f"{sk.icon} {sk.label}", callback_key=button_base_path))

    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


async def _get_admin_manage_request_change_status_text(request: BaseRequest) -> str:
    text = await _build_request_panel_preamble(
        request, "🔄", "Cambio Stato Richiesta",
        include_platform_category=False,
    )
    text += "\n🔹 Scegli il nuovo stato da impostare."
    return text


async def render_admin_reject_request_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        request: BaseRequest
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
                    callback_key=base_path.add(RejectRequestReason.SERVERSIDE)
                )
            ],
            [
                ButtonItem(
                    text="Non disponibile al momento",
                    callback_key=base_path.add(RejectRequestReason.NOT_AVAILABLE)
                )
            ],
            [
                ButtonItem(
                    text="Già disponibile",
                    callback_key=base_path.add(RejectRequestReason.ALREADY_AVAILABLE)
                )
            ],
            [
                ButtonItem(
                    text="Richiesta non chiara",
                    callback_key=base_path.add(RejectRequestReason.UNCLEAR)
                )
            ],
            [
                ButtonItem(
                    text="🔙 Indietro",
                    callback_key=base_path.back())]
        ]
    )


async def _get_admin_reject_request_text(request: BaseRequest) -> str:
    text = await _build_request_panel_preamble(
        request, "❌", "Rifiuto Richiesta",
        include_platform_category=False,
    )
    text += "\n❓ Scegli il motivo del rifiuto o scrivine uno."
    return text


async def render_admin_confirm_rejection_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        request: BaseRequest,
        reason: RejectRequestReason | str
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


async def _get_admin_confirm_rejection_text(request: BaseRequest, rejection_reason: RejectRequestReason | str):
    text = await _build_request_panel_preamble(
        request, "❌", "Rifiuto Richiesta",
        include_platform_category=False,
    )
    if rejection_reason in RejectRequestReason:
        rejection_reason = RejectRequestReason(rejection_reason)
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
    if reason in RejectRequestReason:
        reason = RejectRequestReason(reason)

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
        request: BaseRequest
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
                        str(ix)
                    )
                )
            ]
        ],
        user_id=user_id
    )


def _get_user_request_status_changed_notification_text(request: BaseRequest):
    platform = request.section.platform
    category = request.section.category
    text = (f"🆙 <b>Aggiornamento Richiesta <code>{request.id}</code></b>\n\n"
            f"▫ La tua richiesta (<b>{PLATFORM_CATEGORY_REGISTRY[platform][category].label} {platform.label}</b>) "
            "ha appena ricevuto il suo <b>esito</b>!")

    return text


async def render_last_ten_requests_platform_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _get_last_ten_requests_platform_text()

    buttons = [
        ButtonItem(text=f"{platform.icon} {platform.label}", callback_key=base_path.add(platform))
        for platform in Platform
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
        platform: Platform
):
    cats = PLATFORM_CATEGORY_REGISTRY[platform]
    if len(cats) == 1:
        return await render_last_ten_requests_section_panel(
            update=update,
            context=context,
            section=RequestSection(platform=platform, category=next(iter(cats))),
            base_path=base_path
        )

    text = _get_last_ten_requests_category_text(platform=platform)

    buttons = [
        ButtonItem(text=f"{cat_config.icon} {cat_config.label}", callback_key=base_path.add(cat_key))
        for cat_key, cat_config in cats.items()
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


def _get_last_ten_requests_category_text(platform: Platform):
    text = _get_header() + f"\n\n      → 🔟 <i>Ultime 10 Richieste</i> – {platform.icon} {platform.label}\n\n"

    text += ("▫ Da qui puoi visionare le ultima 10 richieste per categoria.\n\n"
             "🔹 Scegli una categoria.")

    return text


async def render_last_ten_requests_section_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        section: RequestSection
):
    await context.bot.send_chat_action(
        chat_id=update.effective_message.chat_id,
        action=ChatAction.TYPING
    )

    requests = await get_last_n_requests(n=10, platform=section.platform, category=section.category)
    text = await _get_last_ten_requests_section_text(requests=requests, section=section)

    categories = PLATFORM_CATEGORY_REGISTRY.get(section.platform)

    if not categories:
        # RequestSection è valida quindi se succede PLATFORM_CATEGORY_REGISTRY non è completo
        raise ValueError(f"Platform {section.platform.value} not supported!")

    if len(categories) > 1:
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


async def _get_last_ten_requests_section_text(requests: list[BaseRequest], section: RequestSection) -> str:
    text = _get_header() + ("\n\n      → 🔟 <i>Ultime 10 Richieste</i> – "
                            f"{section.platform.icon} {section.category_config.label}\n\n")
    if len(requests) == 0:
        text += ("<blockquote>ℹ Nessuna richiesta ancora formulata per questa sezione.</blockquote>\n\n"
                 "🔹 Scegli un'opzione.")
    else:
        requests_dict = {}
        for request in requests:
            if request.id is None:
                raise ValueError("Request must have an ID!")
            requests_dict[request.id] = request

        text += get_requests_summary(requests=requests, with_authors=True)
        text += ("\n<blockquote>🔍 <b>Maggiori Informazioni</b> – Visiona l'archivio di un utente per maggiori "
                 "informazioni su una richiesta, o contatta Layton.</blockquote>\n\n"
                 "🔹 Scegli un'opzione.")

    return text
