import os.path
from pathlib import Path
from typing import Literal

from pyrogram.types import InlineKeyboardButton
from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from aimods_bot.src.core.exceptions import DatabaseBotException
from aimods_bot.src.helpers.constants.models import Panel, PanelConfig, ButtonItem, RequestData
from aimods_bot.src.helpers.utils.file_utils import delete_os_file
from aimods_bot.src.helpers.utils.request_utils import (get_requests_summary,
                                                        get_request_details, get_request_by_id,
                                                        get_user_cancellable_requests, can_request_be_cancelled,
                                                        get_user_requests_archive, request_data_from_record,
                                                        generate_user_archive_requests_pdf_file)


async def render_user_request_management_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _get_user_request_management_panel_text()

    user_request_management_panel = Panel(
        PanelConfig(
            base_path="user/manage_requests/view_requests",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="📘 Richieste Attive", callback_key="active_requests"),
                    ButtonItem(text="📕 Archivio Richieste", callback_key="requests_archive")
                ],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await user_request_management_panel.render(update=update, context=context)


def _get_user_request_management_panel_text() -> str:
    text = ("👁‍🗨 <b>Gestione Richieste</b>\n\n"
            "▪️ Da qui puoi <b>visionare</b> e <b>gestire</b> le tue <b>richieste</b>.\n\n"
            "<blockquote>ℹ️ L'archivio richieste contiene <u>tutte le tue richieste</u>, "
            "anche quelle non attive.</blockquote>\n\n"
            "🔹 Quale categoria di richieste vuoi gestire?")
    return text


async def render_active_request_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    active_requests = context.user_data["active_requests"]
    text = await _get_active_request_panel_text(requests=active_requests)

    keyboard = []

    if len(active_requests) != 0:
        keyboard.insert(0, [
            ButtonItem(text="📋 Info Richiesta", callback_key="details"),
            ButtonItem(text="🗑 Annulla Richiesta", callback_key="cancel")
        ])

    keyboard.insert(1, [ButtonItem(text="🔙 Indietro", callback_key=None)])

    user_request_panel = Panel(
        PanelConfig(
            base_path="user/manage_requests/view_requests/active_requests",
            text=text,
            keyboard=keyboard
        )
    )

    await user_request_panel.render(update=update, context=context)


async def _get_active_request_panel_text(requests: dict[int, RequestData]) -> str:
    text = "👁‍🗨 <b>Gestione Richieste Attive</b>"

    if len(requests) == 0:
        text += "\n\nℹ️ Non hai nessuna richiesta attiva."
        return text

    text += "\n\n▫️ Ecco le <b>richieste attive</b>.\n\n"

    text += await get_requests_summary(requests=requests)

    text += "\n🔹 Scegli un'opzione."

    return text


async def render_user_request_action_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        action: Literal["details", "cancel"]
):
    text = await _get_user_request_action_panel_text(
        context=context,
        action=action
    )
    keybaord = await _get_user_request_action_panel_keyboard(context=context, action=action)

    user_request_action_panel = Panel(PanelConfig(
        base_path=f"user/manage_requests/view_requests/active_requests/{action}",
        text=text,
        keyboard=keybaord
    ))

    await user_request_action_panel.render(update=update, context=context)


async def _get_user_request_action_panel_text(
        context: ContextTypes.DEFAULT_TYPE,
        action: Literal["details", "cancel"]
) -> str:
    text = f"👁‍🗨 <b>Gestione Richieste Attive</b>"
    if action == "cancel":
        text += "\n\n→ 🗑 <b>Cancellazione</b>"

        requests = await get_user_cancellable_requests(context=context)
        if len(requests) == 0:
            text += "\n\nℹ️ Non hai richieste cancellabili.\n\n"
            return text

    else:  # action == "details"
        text += "\n\n→ 📋 <b>Informazioni</b>"

        requests = context.user_data["active_requests"]
        if len(requests) == 0:
            text += "\n\nℹ️ Non hai richieste da visionare.\n\n"
            return text

    summary = await get_requests_summary(requests=requests)

    text += "\n\n" + summary

    text += f"\n🔹 Scegli quale richiesta vuoi {'visionare' if action == 'details' else 'cancellare'}."

    return text


async def _get_user_request_action_panel_keyboard(
        context: ContextTypes.DEFAULT_TYPE,
        action: Literal["details", "cancel"]
) -> list[list[ButtonItem]]:
    if action == "cancel":
        requests = await get_user_cancellable_requests(context=context)
    else:
        requests = context.user_data["active_requests"]

    if len(requests) != 0:
        keyboard = [[]]
        for n, el in enumerate(requests):
            if len(keyboard[-1]) >= 4:
                keyboard.append([])
            keyboard[-1].append(ButtonItem(text=str(n + 1), callback_key=str(el)))
        keyboard.insert(len(keyboard) + 1, [ButtonItem(text="🔙 Indietro", callback_key=None)])
    else:
        keyboard = [[ButtonItem(text="🔙 Indietro", callback_key=None)]]

    return keyboard


async def render_request_details_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        ix: str
):
    request = get_request_by_id(context=context, ix=ix)
    text = await _get_request_details_panel_text(request=request)

    request_details_panel = Panel(
        PanelConfig(
            base_path=f"user/manage_requests/view_requests/active_requests/details/{str(ix)}",
            text=text,
            keyboard=[
                [ButtonItem(
                    text="📋 Visiona Altra Richiesta",
                    callback_key="user/manage_requests/view_requests/active_requests/details",
                    override_path_generation=True
                )],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await request_details_panel.render(update=update, context=context)


async def _get_request_details_panel_text(request: RequestData) -> str:
    text = (f"👁‍🗨 <b>Gestione Richieste Attive</b>"
            "\n\n→ 📋 <b>Informazioni</b>\n\n"
            "▫️ Ecco i dettagli della tua richiesta.\n\n")

    text += await get_request_details(request=request)
    text += "\n\n🔹 Scegli un'opzione."

    return text


async def render_confirm_cancel_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        ix: str
):
    request = get_request_by_id(context=context, ix=ix)
    if not request:
        raise DatabaseBotException(f"Richiesta {ix} non trovata.")

    if await can_request_be_cancelled(context=context, request=request):
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
                "⚠️ Non puoi più cancellare questa richiesta.\n\n"
                "🔹 Torna indietro per continuare.")
        keyboard = [[ButtonItem(text="🔙 Annulla", callback_key=None)]]

    confirm_cancel_panel = Panel(
        PanelConfig(
            base_path=f"user/manage_requests/view_requests/active_requests/cancel/{ix}",
            text=text,
            keyboard=keyboard
        )
    )

    await confirm_cancel_panel.render(update=update, context=context)


async def _get_confirm_cancel_text(request: RequestData) -> str:
    details_text = await get_request_details(request=request)
    text = ("👁‍🗨 <b>Gestione Richieste Attive</b>\n\n"
            "→ 🗑 <b>Cancellazione</b>\n\n")
    text += details_text
    text += "\n\n🔹 Confermi di voler <b>cancellare</b> questa richesta?"

    return text


async def render_user_request_archive_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    requests = await get_user_requests_archive(user_id=user_id)

    text = await _get_user_request_archive_text(requests=requests)

    p = None
    if not len(requests) == 0:
        await update.effective_message.edit_text(
            text="📕 <b>Archivio Richieste</b>\n\n"
                 "⏳ Un secondo...",
            reply_markup=None,
            parse_mode=ParseMode.HTML
        )
        await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.UPLOAD_DOCUMENT)
        p = await _get_archive_pdf_file(requests=requests, user_id=user_id)

    user_request_archive_panel = Panel(
        PanelConfig(
            base_path="user/manage_requests/view_requests/requests_archive",
            text=text,
            keyboard=[
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await user_request_archive_panel.render(update=update, context=context)

    await context.bot.send_document(
        chat_id=user_id,
        document=p,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                text="🚮 Chiudi",
                callback_data="close"
            )
        ]])
    )

    delete_os_file(str(Path(p).with_suffix(".aux")))
    delete_os_file(str(Path(p).with_suffix(".log")))
    delete_os_file(str(Path(p).with_suffix(".out")))
    delete_os_file(str(Path(p).with_suffix(".tex")))

    # Rimuovo il file dopo 10 minuti per evitare sovraccarichi
    async def _delete_latex_file(context: ContextTypes.DEFAULT_TYPE):
        delete_os_file(path=p)

    context.job_queue.run_once(callback=_delete_latex_file, when=600)


async def _get_user_request_archive_text(requests: list[dict]):
    text = "📕 <b>Archivio Richieste</b>\n\n"

    if len(requests) == 0:
        text += "ℹ️ Non hai formulato alcuna richiesta in passato."
    else:
        text += "▪️ Ecco le richieste che hai formulato in passato in ordine cronologico."

    return text


async def _get_archive_pdf_file(requests: dict, user_id: int):
    if os.path.exists(f"archive_{user_id}_{len(requests)}.pdf"):
        return f"archive_{user_id}_{len(requests)}.pdf"

    requests = [await request_data_from_record(request=el) for el in requests]
    p = await generate_user_archive_requests_pdf_file(
        requests=requests,
        input_path=f"archive_{user_id}_{len(requests)}.tex"
    )
    return p


async def render_request_cancelled_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    text = _get_request_cancelled_panel_text()

    keyboard = [[ButtonItem(text="🔙 Indietro", callback_key=None)]]
    requests = await get_user_cancellable_requests(context=context)

    if len(requests) != 0:
        keyboard.insert(0, [
            ButtonItem(
                text="🗑 Cancella Altra Richiesta",
                callback_key="user/manage_requests/view_requests/active_requests/cancel",
                override_path_generation=True
            )
        ])

    request_cancelled_panel = Panel(
        PanelConfig(
            base_path="user/manage_requests/view_requests/active_requests/cancel",
            text=text,
            keyboard=keyboard
        )
    )

    await request_cancelled_panel.render(update=update, context=context)


def _get_request_cancelled_panel_text():
    text = ("🚮 <b>Richiesta Cancellata</b>\n\n"
            "▫️ La richiesta è stata correttamente cancellata.")
    return text
