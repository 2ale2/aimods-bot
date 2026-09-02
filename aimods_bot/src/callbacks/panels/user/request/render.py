import html
from typing import get_args

from pydantic import HttpUrl
from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext, RequestWizardSession
from aimods_bot.src.core.pydantic import RequestCooldown
from aimods_bot.src.helpers.constants.constants import LOCAL_TZ, EMOJI_HOURGLASS, EMOJI_CHECKMARK, EMOJI_DOT_ORANGE, \
    DATETIME_FORMAT, EMOJI_QUESTION_RED, EMOJI_DOT_BLUE, Platform, EMOJI_NUMBER
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction, UserRoute, UserManageRequestsRoute
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.requests import PLATFORM_CATEGORY_REGISTRY, FIELD_MESSAGES
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel, chunk_buttons
from aimods_bot.src.helpers.utils.time_utils import get_duration_text


async def render_user_has_cooldown_panel(
        update: Update,
        context: CustomContext,
        back_callback: PathBuilder,
        rc: RequestCooldown
):
    cooldown_secs = int(context.pydb.configuration.settings.request.cooldown.total_seconds())
    cooldown_text = get_duration_text(cooldown_secs, with_emoji=False)
    cooldown_end = rc.until.astimezone(LOCAL_TZ).strftime(DATETIME_FORMAT)

    await create_and_render_panel(
        update=update,
        context=context,
        # va bene anche back_callback, perché non ho tasti per avanzare
        text=_get_user_has_cooldown_panel_text(cooldown_end, cooldown_text),
        keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=back_callback)]]
    )


def _get_user_has_cooldown_panel_text(cooldown_end: str, cooldown_text: str):
    return (
        f"{EMOJI_HOURGLASS} <b>Hai già formulato una richiesta.</b>\n\n"
        f"<blockquote>{EMOJI_CHECKMARK} Dopo ogni richiesta, ciascun utente deve attendere "
        f"{cooldown_text}.</blockquote>\n\n"
        f"{EMOJI_DOT_ORANGE} <b>Termine Cooldown</b> — <i>{cooldown_end}</i>"
    )


async def render_user_request_platform_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    await create_and_render_panel(
        update=update,
        context=context,
        text=_get_user_request_platform_text(),
        keyboard=[
            [
                ButtonItem(text="🤖 Android", callback_key=base_path.add(Platform.ANDROID)),
                ButtonItem(text="💻 Windows", callback_key=base_path.add(Platform.WINDOWS)),
            ],
            [
                ButtonItem(text="🍏 iOS", callback_key=base_path.add(Platform.IOS)),
                ButtonItem(text="🖥 MacOS", callback_key=base_path.add(Platform.MACOS))
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


def _get_user_request_platform_text():
    return (
        f"{EMOJI_QUESTION_RED} <b>Nuova Richiesta</b>\n\n"
        f"{EMOJI_DOT_BLUE} Per <b>quale piattaforma</b> vorresti formulare la richiesta?"
    )


async def render_user_request_category_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        platform: Platform
):
    buttons = [
        ButtonItem(
            text=f"{config.icon} {config.label}",
            callback_key=base_path.add(cat)
        )
        for cat, config in PLATFORM_CATEGORY_REGISTRY[platform].items()
    ]

    keyboard = chunk_buttons(buttons=buttons, size=2)
    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])

    await create_and_render_panel(
        update=update,
        context=context,
        text=_get_user_request_category_text(platform=platform),
        keyboard=keyboard
    )


def _get_user_request_category_text(platform: Platform):
    return (
        f"{platform.icon} <b>Nuova Richiesta</b>\n\n"
        f"{EMOJI_DOT_BLUE} Per <b>quale categoria</b> vorresti formulare la richiesta?"
    )


async def render_global_request_wizard_panel(
        update: Update,
        context: CustomContext
):
    wizard = context.pydc.persistent.active_request_wizard
    if not wizard:
        raise ValueError("Trying to build wizard panel with no wizard!")

    text = _get_request_wizard_step_text(wizard=wizard)
    keyboard = _get_request_wizard_step_text_keyboard(wizard=wizard)

    returned_id = await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=keyboard,
        message_id=wizard.request_msg_id
    )

    if returned_id:
        context.pydc.persistent.active_request_wizard.request_msg_id = returned_id


def _get_request_wizard_step_text(wizard: RequestWizardSession) -> str:
    draft = wizard.draft
    cat_conf = draft.section.category_config

    text = f"{draft.section.platform.icon} <b>Nuova Richiesta – {cat_conf.label}</b>\n\n"

    for flow_el in draft.FLOW:
        field_name = flow_el.value
        if flow_el == wizard.requesting:
            add_label = "🖋"
        elif field_name in draft.model_fields_set:
            label = getattr(draft, field_name)
            if isinstance(label, HttpUrl):
                add_label = f"<a href=\"{str(label)}\">🔗 Link</a>"
            elif isinstance(label, bool):
                add_label = f"{'✔️' if label else '✖️'}"
            else:
                add_label = html.escape(str(label))
        else:
            add_label = f"{cat_conf.icon}"

        text += f"{EMOJI_DOT_ORANGE} <b><i>{flow_el.label}</i></b> – {add_label}\n\n"

    if wizard.requesting:
        if wizard.requesting not in FIELD_MESSAGES:
            raise ValueError(f"{wizard.requesting} is missing in FIELD_MESSAGES!")

        text += FIELD_MESSAGES[wizard.requesting].get_prompt(draft.section.category)
    else:
        text += ("🔹 Verifica i dettagli della tua richiesta. "
                 "<b>Premi uno dei tasti per modificare un elemento</b>, oppure <b>conferma per inviarla</b>.\n\n"
                 "<blockquote>⚠️ <b>Assicurati che i dettagli siano chiari</b>, "
                 "altrimenti la tua richiesta sarà <b>bocciata</b>.</blockquote>")

    return text


def _get_request_wizard_step_text_keyboard(wizard: RequestWizardSession) -> list[list[ButtonItem]]:
    draft = wizard.draft
    from_notification = wizard.from_notification
    first_requesting = (wizard.requesting == draft.FLOW[0])
    if from_notification:
        cancel_button = ButtonItem(text="🚮 Chiudi", callback_key=GlobalAction.CLOSE)
    else:
        cancel_button = ButtonItem(text="🔙 Home", callback_key=UserRoute.ROOT)

    if wizard.requesting:
        keyboard = []
        field = wizard.requesting.value
        field_type = draft.model_fields[field].annotation
        is_boolean_field = (field_type is bool) or (bool in get_args(field_type))
        if is_boolean_field:
            keyboard.append([
                ButtonItem(text="✅ Sì", callback_key=GlobalAction.YES),
                ButtonItem(text="❌ No", callback_key=GlobalAction.NO)
            ])
        show_back = not (from_notification and first_requesting)
        service_buttons = []
        if show_back:
            service_buttons.append(ButtonItem(text="🔙 Indietro", callback_key=GlobalAction.REQUEST_WIZARD_BACK))
        service_buttons.append(cancel_button)
        keyboard.append(service_buttons)
        return keyboard
    else:
        buttons = []
        for count, flow_el in enumerate(draft.FLOW, start=1):
            buttons.append(ButtonItem(text=f"{EMOJI_NUMBER[count]} {flow_el.label}", callback_key=flow_el))

        keyboard = chunk_buttons(buttons=buttons, size=2)
        keyboard.append([ButtonItem(text="✅ Conferma", callback_key=GlobalAction.CONFIRM), cancel_button])
        return keyboard


async def render_request_wizard_confirmation_panel(
        update: Update,
        context: CustomContext,
        from_notification: bool
):
    await create_and_render_panel(
        update=update,
        context=context,
        text=_get_request_wizard_confirmation_text(),
        keyboard=_get_request_wizard_confirmation_keyboard(from_notification=from_notification)
    )


def _get_request_wizard_confirmation_text():
    return ("✅ <b>Richiesta Inviata Correttamente!</b>\n\n"
            "🔹 Puoi monitorare lo stato di <b>avanzamento in tempo reale</b> dal tuo pannello di controllo. "
            "<b>Riceverai una notifica</b> quando la tua richiesta verrà chiusa.\n\n"
            "ℹ️ Puoi disattivare le notifiche dalle impostazioni.")


def _get_request_wizard_confirmation_keyboard(from_notification: bool):
    if from_notification:
        back_button = ButtonItem(text="📪 Chiudi", callback_key=GlobalAction.CLOSE_MENU)
    else:
        back_button = ButtonItem(text="🏠 Torna alla Home", callback_key=PathBuilder(UserRoute.ROOT))

    return [
            [
                ButtonItem(
                    text="♟️ Gestisci Richieste",
                    callback_key=PathBuilder(UserRoute.ROOT, UserRoute.VIEW_REQUESTS)
                ),
                ButtonItem(
                    text="⚙️ Gestisci Imp.",
                    callback_key=PathBuilder(UserRoute.ROOT, UserRoute.MANAGE_SETTINGS)
                )
            ],
            [back_button]
    ]


async def render_cant_request_panel(
        update: Update,
        context: CustomContext,
        back_callback: PathBuilder,
        message: str,
        keyboard: list[list[ButtonItem]] | None = None
):
    await create_and_render_panel(
        update=update,
        context=context,
        text=message,
        keyboard=keyboard or [[ButtonItem(text="🔙 Indietro", callback_key=back_callback)]]
    )


async def render_section_notification_activated_panel(
        update: Update,
        context: CustomContext,
        section: RequestSection
):
    cat_conf = PLATFORM_CATEGORY_REGISTRY[section.platform][section.category]
    text = ("✅ <b>Notifiche Sezione Attivate</b>\n\n"
            "🔹 Hai attivato le notifiche per la sezione "
            f"{cat_conf.icon} <b>{section.platform.label} ({cat_conf.label})</b>. "
            "Riceverai un messaggio da me quando questa sezione verrà riaperta.")

    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="❔ Formula Richiesta",
                    callback_key=PathBuilder(UserRoute.ROOT, UserRoute.ADD_REQUEST)
                ),
                ButtonItem(text="🏠 Home", callback_key=PathBuilder(UserRoute.ROOT))
            ]
        ]
    )


async def render_user_has_an_active_request_wizard_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        section: RequestSection
):
    text = ("❔ Risulta che stai già facendo un'altra richiesta per la sezione\n\n"
            f"        {section.platform.icon} <b>{section.category_config.label}</b>\n\n"
            "🔸 Vuoi riprenderla oppure formularne un'altra?\n\n"
            "<blockquote>⚠️ Se ne formuli una nuova, <b>i dettagli già forniti dell'altra richiesta "
            "in fase di formulazione andranno persi</b>.</blockquote>")

    keyboard = [
        [
            ButtonItem(
                text="✏️ Continuo la Precedente",
                callback_key=base_path.add(UserManageRequestsRoute.CONTINUE_REQUEST)
            )
        ],
        [
            ButtonItem(
                text="➕ Ne formulo un'altra",
                callback_key=base_path.add(UserManageRequestsRoute.DISMISS_REQUEST)
            )
        ]
    ]

    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=keyboard
    )


def section_notifications_button(context: CustomContext, section: RequestSection) -> ButtonItem | None:
    enabled = context.pydc.persistent.user_notifications.section_opening_notifications[section.platform][section.category]
    if enabled:
        return None
    return ButtonItem(
        text="🔔 Attiva Notifiche Sezione",
        callback_key=PathBuilder(
            UserRoute.ADD_REQUEST, section.platform, section.category,
            UserManageRequestsRoute.ENABLE_SECTION_NOTIFICATIONS
        )
    )
