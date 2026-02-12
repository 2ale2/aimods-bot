import os.path
from pathlib import Path
from typing import Literal, Optional

from pyrogram.types import InlineKeyboardButton
from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import DatabaseBotException
from aimods_bot.src.core.pydantic import Request
from aimods_bot.src.helpers.constants.models import ButtonItem
from aimods_bot.src.helpers.utils.file_utils import delete_os_file
from aimods_bot.src.helpers.utils.request_utils import (get_requests_summary,
                                                        get_request_details,
                                                        get_user_requests_archive,
                                                        generate_user_archive_requests_pdf_file)
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)


async def render_user_request_management_panel(update: Update, context: CustomContext):
    text = _get_user_request_management_panel_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="user/view_requests",
        text=text,
        keyboard=[
            [
                ButtonItem(text="📘 Richieste Attive", callback_key="active_requests"),
                ButtonItem(text="📕 Archivio Richieste", callback_key="requests_archive")
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


def _get_user_request_management_panel_text() -> str:
    text = ("👁‍🗨 <b>Gestione Richieste</b>\n\n"
            "▪️ Da qui puoi <b>visionare</b> e <b>gestire</b> le tue <b>richieste</b>.\n\n"
            "<blockquote>ℹ️ L'archivio richieste contiene <u>tutte le tue richieste</u>, "
            "anche quelle non attive.</blockquote>\n\n"
            "🔹 Quale categoria di richieste vuoi gestire?")
    return text


async def render_active_request_panel(
        update: Update,
        context: CustomContext
):
    active_requests = context.user_active_requests
    text = _get_active_request_panel_text(requests=active_requests)

    keyboard = []

    if active_requests:
        keyboard.append([
            ButtonItem(text="📋 Info Richiesta", callback_key="details"),
            ButtonItem(text="🗑 Annulla Richiesta", callback_key="cancel")
        ])

    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=None)])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="user/view_requests/active_requests",
        text=text,
        keyboard=keyboard
    )


def _get_active_request_panel_text(requests: dict[int, Request]) -> str:
    text = "👁‍🗨 <b>Gestione Richieste Attive</b>"

    if not requests:
        text += "\n\nℹ️ Non hai nessuna richiesta attiva."
        return text

    text += "\n\n▫️ Ecco le <b>richieste attive</b>.\n\n"

    text += get_requests_summary(requests=requests)

    text += "\n🔹 Scegli un'opzione."

    return text


async def render_user_request_action_panel(
        update: Update,
        context: CustomContext,
        action: Literal["details", "cancel"]
):
    requests = context.user_cancellable_requests if action == "cancel" else context.user_active_requests

    text = await _get_user_request_action_panel_text(
        action=action,
        requests=requests
    )
    keyboard = await _get_user_request_action_panel_keyboard(context=context, action=action)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"user/view_requests/active_requests/{action}",
        text=text,
        keyboard=keyboard
    )


async def _get_user_request_action_panel_text(
        action: Literal["details", "cancel"],
        requests: dict[int, Request]
) -> str:
    text = f"👁‍🗨 <b>Gestione Richieste Attive</b>"
    if action == "cancel":
        text += "\n\n→ 🗑 <b>Cancellazione</b>"
        if len(requests) == 0:
            text += "\n\nℹ️ Non hai richieste cancellabili.\n\n"
            return text

    else:  # action == "details"
        text += "\n\n→ 📋 <b>Informazioni</b>"
        if len(requests) == 0:
            text += "\n\nℹ️ Non hai richieste da visionare.\n\n"
            return text

    summary = get_requests_summary(requests=requests)

    text += "\n\n" + summary

    text += f"\n🔹 Scegli quale richiesta vuoi {'visionare' if action == 'details' else 'cancellare'}."

    return text


async def _get_user_request_action_panel_keyboard(
        context: CustomContext,
        action: Literal["details", "cancel"]
) -> list[list[ButtonItem]]:
    if action == "cancel":
        requests = context.user_cancellable_requests
    else:
        requests = context.user_active_requests

    if len(requests) != 0:
        keyboard = [[]]
        for n, ix in enumerate(requests):
            request = requests[ix]
            if len(keyboard[-1]) >= 4:
                keyboard.append([])
            keyboard[-1].append(ButtonItem(text=str(n + 1), callback_key=request.id))
        keyboard.insert(len(keyboard) + 1, [ButtonItem(text="🔙 Indietro", callback_key=None)])
    else:
        keyboard = [[ButtonItem(text="🔙 Indietro", callback_key=None)]]

    return keyboard


async def render_request_details_panel(
        update: Update,
        context: CustomContext,
        ix: int
):
    request = context.get_active_request_by_id(ix=ix)
    text = await _get_request_details_panel_text(request=request)

    keyboard = [
        [ButtonItem(text="📋 Visiona Altra Richiesta", callback_key=None)],
        [ButtonItem(text="🔙 Indietro", callback_key="user/view_requests", override_path_generation=True)]
    ]
    if request.is_active:
        notifications = request.status_change_notifications
        keyboard.insert(1, [
            ButtonItem(
                text=f"{'🔔 Attiva' if not notifications else '🔕 Disattiva'} Notifiche Esito",
                callback_key=f"{'enable_' if not notifications else 'disable_'}notifications"
            )
        ])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"user/view_requests/active_requests/details/{ix}",
        text=text,
        keyboard=keyboard
    )


async def _get_request_details_panel_text(request: Request) -> str:
    text = (f"👁‍🗨 <b>Gestione Richieste Attive</b>"
            "\n\n→ 📋 <b>Informazioni</b>\n\n"
            "▫️ Ecco i dettagli della tua richiesta.\n\n")

    text += await get_request_details(request=request)
    text += "\n\n🔹 Scegli un'opzione."

    return text


async def render_confirm_cancel_panel(
        update: Update,
        context: CustomContext,
        ix: int
):
    request = context.get_active_request_by_id(ix=ix)
    if not request:
        raise DatabaseBotException(f"Richiesta {ix} non trovata.")

    timer_sec = context.pydb.configuration.settings.request.cancel_timer
    if request.can_be_cancelled(timer_sec):
        text = await _get_confirm_cancel_text(request=request)
        keyboard = [
            [
                ButtonItem(text="🌪 Conferma", callback_key="yes"),
                ButtonItem(text="🔙 Annulla", callback_key=None)
            ]
        ]
    else:
        text = ("👁‍🗨 <b>Gestione Richieste Attive</b>\n\n"
                "→ 🗑 <b>Cancellazione</b>\n\n"
                "<blockquote>⚠️ Non puoi più cancellare questa richiesta.</blockquote>\n\n"
                "🔹 Torna indietro per continuare.")
        keyboard = [[ButtonItem(text="🔙 Annulla", callback_key=None)]]

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"user/view_requests/active_requests/cancel/{ix}",
        text=text,
        keyboard=keyboard
    )


async def _get_confirm_cancel_text(request: Request) -> str:
    details_text = await get_request_details(request=request)
    text = ("👁‍🗨 <b>Gestione Richieste Attive</b>\n\n"
            "→ 🗑 <b>Cancellazione</b>\n\n")
    text += details_text
    text += "\n\n🔹 Confermi di voler <b>cancellare</b> questa richesta?"

    return text


async def render_user_request_archive_panel(
        update: Update,
        context: CustomContext,
        user_id: Optional[int] = None,
        requested_by_admin: bool = False
):
    user_id = user_id or update.effective_user.id
    requests = await get_user_requests_archive(user_id=user_id)

    text = await _get_user_request_archive_text(requests=requests, requested_from_admin=requested_by_admin)

    p = None
    if not len(requests) == 0:
        archive_text = (f"📕 <b>Archivio Richieste {'Utente' if requested_by_admin else ''}</b>\n\n"
                "⏳ Un secondo...")
        try:
            await update.effective_message.edit_text(
                text=archive_text,
                reply_markup=None,
                parse_mode=ParseMode.HTML
            )
        except BadRequest:
            if not context.pydc.persistent.bot_message_id:
                raise
            await context.bot.edit_message_text(
                chat_id=update.effective_user.id,
                message_id=context.pydc.persistent.bot_message_id,
                text=archive_text,
                parse_mode=ParseMode.HTML
            )
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        p = await _get_archive_pdf_file(requests=requests, user_id=user_id)

    if requested_by_admin:
        base_path = f"admin/manage_requests/user_requests_archive/{user_id}"
    else:
        base_path = "user/view_requests/requests_archive"

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ],
        message_id=context.pydc.persistent.bot_message_id
    )

    context.pydc.persistent.bot_message_id = None
    if p:
        await context.bot.send_document(
            chat_id=update.effective_user.id,
            document=p,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    text="🚮 Chiudi",
                    callback_data="close_menu"
                )
            ]])
        )

        await delete_os_file(str(Path(p).with_suffix(".aux")))
        await delete_os_file(str(Path(p).with_suffix(".log")))
        await delete_os_file(str(Path(p).with_suffix(".out")))
        await delete_os_file(str(Path(p).with_suffix(".tex")))

        # Rimuovo il file dopo 10 minuti per evitare sovraccarichi
        async def _delete_latex_file(context: CustomContext):
            await delete_os_file(path=p)

        job = context.job_queue.get_jobs_by_name("_delete_latex_file")
        if job:
            job[0].schedule_removal()
        context.job_queue.run_once(callback=_delete_latex_file, when=600)


async def _get_user_request_archive_text(requests: list[Request], requested_from_admin: bool = False):
    text = "📕 <b>Archivio Richieste</b>\n\n"

    if requested_from_admin:
        if len(requests) == 0:
            text += "<blockquote>ℹ️ L'utente non ha ancora formulato alcuna richiesta.</blockquote>"
        else:
            text += "▪️ Ecco le richieste che l'utente ha formulato in passato in ordine cronologico."
    else:
        if len(requests) == 0:
            text += "<blockquote>ℹ️ Non hai formulato alcuna richiesta in passato.</blockquote>"
        else:
            text += "▪️ Ecco le richieste che hai formulato in passato in ordine cronologico."

    return text


async def _get_archive_pdf_file(requests: list[Request], user_id: int):
    if os.path.exists(f"archive_{user_id}_{len(requests)}.pdf"):
        return f"archive_{user_id}_{len(requests)}.pdf"

    p = await generate_user_archive_requests_pdf_file(
        requests=requests,
        input_path=f"archive_{user_id}_{len(requests)}.tex"
    )
    return p


async def render_request_cancelled_panel(
        update: Update,
        context: CustomContext
):
    text = _get_request_cancelled_panel_text()

    keyboard = [[ButtonItem(text="🔙 Indietro", callback_key=None)]]
    requests = context.user_cancellable_requests

    if len(requests) != 0:
        keyboard.insert(0, [
            ButtonItem(
                text="🗑 Cancella Altra Richiesta",
                callback_key="user/view_requests/active_requests/cancel",
                override_path_generation=True
            )
        ])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="user/view_requests/active_requests/cancel",
        text=text,
        keyboard=keyboard
    )


def _get_request_cancelled_panel_text():
    text = ("🚮 <b>Richiesta Cancellata</b>\n\n"
            "▫️ La richiesta è stata correttamente cancellata.")
    return text
