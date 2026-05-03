from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import Request
from aimods_bot.src.helpers.constants.conversation_paths.navigation import UserManageRequestsRoute, UserRoute, \
    GlobalAction
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.request_utils import (get_requests_summary,
                                                        get_request_details)
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel

log = logger.getChild(__name__)


async def render_user_request_management_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _get_user_request_management_panel_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="📘 Richieste Attive",
                    callback_key=base_path.add(UserManageRequestsRoute.ACTIVE)
                ),
                ButtonItem(
                    text="📕 Archivio Richieste",
                    callback_key=base_path.add(UserManageRequestsRoute.REQUEST_ARCHIVE)
                )
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


def _get_user_request_management_panel_text() -> str:
    text = ("👁‍🗨 <b>Gestione Richieste</b>\n\n"
            "▪️ Da qui puoi <b>visionare</b> e <b>gestire</b> le tue <b>richieste</b>.\n\n"
            "<blockquote>ℹ️ L'archivio richieste contiene <u>tutte le tue richieste</u>, "
            "anche quelle non attive.</blockquote>\n\n"
            "🔹 Quale categoria di richieste vuoi gestire?")
    return text


async def render_user_manage_active_requests_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    requests = context.user_active_requests

    text = _get_user_manage_active_requests_main_panel(requests=requests)

    keyboard = await _get_user_manage_requests_main_panel_keyboard(base_path=base_path, requests=requests)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


def _get_user_manage_active_requests_main_panel(requests: dict[int, Request]) -> str:
    text = "👁‍🗨 <b>Gestione Richieste Attive</b>"

    if not requests:
        text += "\n\nℹ️ Non hai nessuna richiesta attiva."
        return text

    text += "\n\n▫️ Ecco le tue <b>richieste attive</b>.\n\n"

    text += get_requests_summary(requests=requests)

    text += "\n🔹 Scegli quale richiesta gestire."

    return text


async def _get_user_manage_requests_main_panel_keyboard(
        base_path: PathBuilder,
        requests: dict[int, Request]
) -> list[list[ButtonItem]]:
    if len(requests):
        keyboard = [[]]
        for n, ix in enumerate(requests):
            request = requests[ix]
            if len(keyboard[-1]) >= 4:
                keyboard.append([])
            keyboard[-1].append(ButtonItem(text=str(n + 1), callback_key=base_path.add(str(request.id))))
        keyboard.insert(len(keyboard) + 1, [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])
    else:
        keyboard = [[ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]]

    return keyboard


async def render_manage_selected_request_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        request: Request
):
    text = await _get_manage_selected_request_text(request=request)

    keyboard = [
        [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
    ]

    timer_sec = context.pydb.configuration.settings.request.cancel_timer
    if request.can_be_cancelled(timer_sec):
        keyboard.insert(0, [
            ButtonItem(
                text="🗑 Annulla Richiesta",
                callback_key=base_path.add(UserManageRequestsRoute.CANCEL)
            )
        ])

    if request.is_active:
        notification = request.status_change_notifications
        if notification:
            notify_toggle_button = UserManageRequestsRoute.DISABLE_STATUS_NOTIFICATION
        else:
            notify_toggle_button = UserManageRequestsRoute.ENABLE_STATUS_NOTIFICATION

        keyboard.insert(0, [
            ButtonItem(
                text=f"{'🔕 Disattiva' if notification else '🔔 Attiva'} Notifiche Esito",
                callback_key=base_path.add(notify_toggle_button)
            )
        ])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


async def _get_manage_selected_request_text(request: Request) -> str:
    text = (f"👁‍🗨 <b>Gestione Richieste Attive</b>"
            "\n\n→ 📋 <b>Informazioni</b>\n\n"
            "▫️ Ecco i dettagli della richiesta.\n\n")

    text += await get_request_details(request=request)
    text += "\n\n🔹 Scegli un'opzione."

    return text


async def render_confirm_cancel_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        request: Request
):
    timer_sec = context.pydb.configuration.settings.request.cancel_timer
    if request.can_be_cancelled(timer_sec):
        text = await _get_confirm_cancel_text(request=request)
        keyboard = [
            [
                ButtonItem(text="🌪 Conferma", callback_key=base_path.add(GlobalAction.YES)),
                ButtonItem(text="🔙 Annulla", callback_key=base_path.back())
            ]
        ]
    else:
        text = ("👁‍🗨 <b>Gestione Richieste Attive</b>\n\n"
                "→ 🗑 <b>Cancellazione</b>\n\n"
                "<blockquote>⚠️ Non puoi più cancellare questa richiesta.</blockquote>\n\n"
                "🔹 Torna indietro per continuare.")
        keyboard = [[ButtonItem(text="🔙 Annulla", callback_key=base_path.back())]]

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


async def _get_confirm_cancel_text(request: Request) -> str:
    details_text = await get_request_details(request=request)
    text = ("👁‍🗨 <b>Gestione Richieste Attive</b>\n\n"
            "→ 🗑 <b>Cancellazione</b>\n\n")
    text += details_text
    text += "\n\n🔹 Confermi di voler <b>cancellare</b> questa richiesta?"

    return text


async def render_request_cancelled_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    text = _get_request_cancelled_panel_text()

    keyboard = [
        [ButtonItem(text="🔙 Indietro", callback_key=base_path)],
        [ButtonItem(text="🏠 Home", callback_key=PathBuilder(UserRoute.ROOT))]
    ]

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


def _get_request_cancelled_panel_text():
    text = ("🚮 <b>Richiesta Cancellata</b>\n\n"
            "▫️ La richiesta è stata correttamente cancellata.")
    return text
