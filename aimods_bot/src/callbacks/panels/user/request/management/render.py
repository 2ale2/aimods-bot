from typing import Literal

from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.core.exceptions import DatabaseBotException
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.utils.request_utils import get_user_active_requests, can_request_be_cancelled, \
    get_requests_summary, get_request_details, get_request_by_id


async def render_user_request_management_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _get_user_request_management_panel_text()

    user_request_management_panel = Panel(
        PanelConfig(
            base_path="user/manage_requests/view_request",
            text=text,
            keyboard=[
                [
                    ButtonItem(text=f"{PLATFORM_DETAILS['android']['icon']} Android", callback_key="android"),
                    ButtonItem(text=f"{PLATFORM_DETAILS['windows']['icon']} Windows", callback_key="windows")
                ],
                [
                    ButtonItem(text=f"{PLATFORM_DETAILS['ios']['icon']} iOS", callback_key="ios"),
                    ButtonItem(text=f"{PLATFORM_DETAILS['macos']['icon']} MacOS", callback_key="macos")
                ],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await user_request_management_panel.render(update=update, context=context)


def _get_user_request_management_panel_text() -> str:
    text = ("👁‍🗨 <b>Gestione Richieste</b>\n\n"
            "▫️ Da qui puoi <b>visionare</b> e <b>gestire</b> le tue <b>richieste</b>."
            "🔹 Quale categoria di richieste vuoi gestire?")
    return text


async def render_user_request_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        platform: Literal["android", "windows", "ios", "macos"]
):
    requests = get_user_active_requests(context=context, platform=platform)
    text = _get_user_request_panel_text(context=context, platform=platform, requests=requests)

    keyboard = []

    if len(requests) != 0:
        keyboard[0].append([
            ButtonItem(text="📋 Info Richiesta", callback_key="details"),
            ButtonItem(text="🗑 Annulla Richiesta", callback_key="cancel")
        ])

    keyboard.insert(1, [ButtonItem(text="🔙 Indietro", callback_key=None)])

    user_request_panel = Panel(
        PanelConfig(
            base_path=f"user/manage_requests/view_request/{platform}",
            text=text,
            keyboard=keyboard
        )
    )

    await user_request_panel.render(update=update, context=context)


def _get_user_request_panel_text(
        context: ContextTypes.DEFAULT_TYPE,
        platform: Literal["android", "windows", "ios", "macos"],
        requests: dict
) -> str:
    text = f"👁‍🗨 <b>Gestione Richieste – <i>{PLATFORM_DETAILS[platform]['label']}</i></b>"

    if len(requests) == 0:
        text += "\n\nℹ️ Non hai formulato alcuna richiesta per questa piattaforma."
        return text

    text += "\n\n▫️ Ecco le <b>richieste</b> che hai formulato."

    text += get_requests_summary(context=context, requests=requests)

    text += f"\n\n🔹 Scegli un opzione."

    return text


async def render_user_request_action_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        platform: Literal["android", "windows", "ios", "macos"],
        action: Literal["details", "cancel"]
):
    requests = get_user_active_requests(context=context, platform=platform)
    text = _get_user_request_action_panel_text(context=context, platform=platform, action=action, requests=requests)
    keybaord = _get_user_request_action_panel_keyboard(context=context, action=action, requests=requests)

    user_request_action_panel = Panel(PanelConfig(
        base_path=f"user/manage_requests/view_request/{platform}/{action}",
        text=text,
        keyboard=keybaord
    ))

    await user_request_action_panel.render(update=update, context=context)


async def _get_user_request_action_panel_text(
        context: ContextTypes.DEFAULT_TYPE,
        platform: Literal["android", "windows", "ios", "macos"],
        action: Literal["details", "cancel"],
        requests: dict
) -> str:
    text = f"👁‍🗨 <b>Gestione Richieste – <i>{PLATFORM_DETAILS[platform]['label']}</i></b>"
    if action == "cancel":
        text += "\n\n→ 🗑 <b>Cancellazione</b>"
    else:  # action == "details"
        text += "\n\n→ 📋 <b>Informazioni</b>"

    summary = get_requests_summary(context=context, requests=requests, only_cancellable=action == "cancel")

    if not summary:
        if action == "cancel":
            text += "ℹ️ Non hai richieste cancellabili."
        else:
            text += "ℹ️ Non hai richieste da visionare."
        return text

    text += f"🔹 Scegli quale richiesta vuoi {'visionare' if action == 'details' else 'cancellare'}."

    return text


async def _get_user_request_action_panel_keyboard(
        context: ContextTypes.DEFAULT_TYPE,
        action: Literal["details", "cancel"],
        requests: dict
) -> list[list[ButtonItem]]:

    keyboard = []
    for n, el in enumerate(requests):
        if action == "cancel" and not await can_request_be_cancelled(context=context, ix=el):
            continue

        if len(keyboard[-1]) >= 4:
            keyboard.append([])
        keyboard[-1].append(ButtonItem(text=str(n), callback_key=str(el)))
    keyboard.insert(len(keyboard) + 1, [ButtonItem(text="🔙 Indietro", callback_key=None)])

    return keyboard


async def render_request_details_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        platform: Literal["android", "windows", "ios", "macos"],
        ix: int
):
    request = await get_request_by_id(context=context, ix=ix)
    text = _get_request_details_panel_text(platform=platform, request=request)

    request_details_panel = Panel(
        PanelConfig(
            base_path=f"user/manage_requests/view_request/{platform}/details/{str(ix)}",
            text=text,
            keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=None)]]
        )
    )

    await request_details_panel.render(update=update, context=context)


def _get_request_details_panel_text(
        platform: Literal["android", "windows", "ios", "macos"],
        request: dict
) -> str:
    text = (f"👁‍🗨 <b>Gestione Richieste – <i>{PLATFORM_DETAILS[platform]['label']}</i></b>"
            "\n\n→ 📋 <b>Informazioni</b>\n\n"
            "▫️ Ecco i dettagli della tua richiesta.\n\n")

    text += get_request_details(request=request)
    text += "🔹 Scegli un'opzione."

    return text


async def render_confirm_cancel_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        platform: Literal["android", "windows", "ios", "macos"],
        ix: int
):
    request = await get_request_by_id(context=context, ix=ix)
    if not request:
        raise DatabaseBotException(f"Errore durante il fetch della richiesta {ix}")

    text = _get_confirm_cancel_text(platform=platform, request=request)

    confirm_cancel_panel = Panel(
        PanelConfig(
            base_path=f"user/manage_requests/view_request/{platform}/cancel/{str(ix)}",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="🌪 Conferma", callback_key="yes"),
                    ButtonItem(text="🔙 Annulla", callback_key=None)
                ]
            ]
        )
    )

    await confirm_cancel_panel.render(update=update, context=context)


async def _get_confirm_cancel_text(
        platform: Literal["android", "windows", "ios", "macos"],
        request: dict
):
    details_text = get_request_details(request=request)
    text = (f"👁‍🗨 <b>Gestione Richieste – <i>{PLATFORM_DETAILS[platform]['label']}</i></b>\n\n"
            "→ 🗑 <b>Cancellazione</b>\n\n")
    text += details_text
    text += "\n\n🔹 Confermi di voler cancellare questa richesta?"

    return text
