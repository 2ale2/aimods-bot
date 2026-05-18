import html
from typing import get_args

from pydantic import HttpUrl
from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext, RequestWizardSession
from aimods_bot.src.core.pydantic import RequestCooldown
from aimods_bot.src.helpers.constants.constants import LOCAL_TZ, EMOJI_HOURGLASS, EMOJI_CHECKMARK, EMOJI_DOT_ORANGE, \
    DATETIME_FORMAT, EMOJI_QUESTION_RED, EMOJI_WARNING, EMOJI_ESCLAMATION_RED, EMOJI_DOT_BLUE, Platform, \
    EMOJI_NUMBER
from aimods_bot.src.helpers.constants.conversation_paths.navigation import GlobalAction, UserRoute
from aimods_bot.src.helpers.models.requests import REQUESTS_LAYOUT_REGISTRY, FIELD_MESSAGES
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel, chunk_buttons
from aimods_bot.src.helpers.utils.time_utils import get_duration_text


async def render_user_has_cooldown_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        rc: RequestCooldown
):
    cooldown_secs = int(context.pydb.configuration.settings.request.cooldown.total_seconds())
    cooldown_text = get_duration_text(cooldown_secs, with_emoji=False)
    cooldown_end = rc.until.astimezone(LOCAL_TZ).strftime(DATETIME_FORMAT)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=_get_user_has_cooldown_panel_text(cooldown_end, cooldown_text),
        keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]]
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
        base_path=base_path,
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
            callback_key=cat_enum.value
        )
        for cat_enum, config in REQUESTS_LAYOUT_REGISTRY[platform]
    ]

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=_get_user_request_category_text(platform=platform),
        keyboard=chunk_buttons(buttons=buttons, size=2)
    )


def _get_user_request_category_text(platform: Platform):
    return (
        f"{platform.icon} <b>Nuova Richiesta</b>\n\n"
        f"{EMOJI_DOT_BLUE} Per <b>quale piattaforma</b> vorresti formulare la richiesta?"
    )


async def render_user_cant_request_panel(update: Update, context: CustomContext, reason: str):
    await create_and_render_panel(
        update=update,
        context=context,
        base_path="user/view_requests",
        text=_get_user_cant_request_text(reason),
        keyboard=[
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


def _get_user_cant_request_text(reason: str):
    return (
        f"{EMOJI_WARNING} <b>Nuova Richiesta</b>\n\n"
        f"{EMOJI_ESCLAMATION_RED} Non puoi effettuare una nuova richiesta al momento.\n\n"
        f"▪ <b>Motivo</b> – {reason}"
    )


async def render_global_request_wizard_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    wizard = context.pydc.persistent.active_request_wizard
    if not wizard:
        raise ValueError("Trying to build wizard panel with no wizard!")

    text = _get_request_wizard_step_text(wizard=wizard)
    keyboard = _get_request_wizard_step_text_keyboard(wizard=wizard)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard,
        message_id=wizard.request_msg_id
    )


def _get_request_wizard_step_text(wizard: RequestWizardSession) -> str:
    draft = wizard.draft
    cat_conf = REQUESTS_LAYOUT_REGISTRY[draft.platform][draft.category]

    text = f"{draft.platform.icon} <b>Nuova Richiesta – {cat_conf.label}</b>\n\n"

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

        text += f"{EMOJI_DOT_ORANGE} {flow_el.label} – {add_label}\n\n"

    if wizard.requesting:
        text += FIELD_MESSAGES.get(wizard.requesting).get_prompt(draft.category)
    else:
        text += ("🔹 Verifica i dettagli della tua richiesta. "
                 "<b>Premi uno dei tasti per modificare un elemento</b>, oppure <b>conferma per inviarla</b>.\n\n"
                 "<blockquote>⚠️ Assicurati che i dettagli siano chiari, "
                 "altrimenti la tua richiesta sarà bocciata.</blockquote>")

    return text


def _get_request_wizard_step_text_keyboard(wizard: RequestWizardSession) -> list[list[ButtonItem]]:
    draft = wizard.draft
    from_notification = wizard.from_notification
    if from_notification:
        cancel_button = ButtonItem(text="🚮 Chiudi", callback_key=GlobalAction.CLOSE)
    else:
        cancel_button = ButtonItem(text="🔙 Home", callback_key=PathBuilder(UserRoute.ROOT))

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
        keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=GlobalAction.REQUEST_WIZARD_BACK), cancel_button])
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
        base_path: PathBuilder,
        from_notification: bool
):
    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=_get_request_wizard_confirmation_text(),
        keyboard=_get_request_wizard_confirmation_keyboard(from_notification=from_notification)
    )


def _get_request_wizard_confirmation_text():
    return ("✅ <b>Richiesta Inviata Correttamente!</b>\n\n"
            "🔹 Puoi monitorare lo stato di avanzamento in tempo reale dal tuo pannello di controllo. "
            "Riceverai una notifica quando la tua richiesta verrà chiusa.\n\n"
            "ℹ️ Puoi disattivare le notifiche dalle impostazioni.")


def _get_request_wizard_confirmation_keyboard(from_notification: bool):
    if from_notification:
        back_button = ButtonItem(text="📪 Chiudi", callback_key=GlobalAction.CLOSE)
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
        base_path: PathBuilder,
        message: str
):
    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=message,
        keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]]
    )
