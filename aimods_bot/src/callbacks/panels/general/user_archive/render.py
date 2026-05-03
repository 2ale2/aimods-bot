import os
from pathlib import Path

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import Request
from aimods_bot.src.helpers.constants.conversation_paths.navigation import AdminRoute, UserRoute, GlobalAction
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.file_utils import delete_os_file
from aimods_bot.src.helpers.utils.request_utils import get_user_requests_archive, \
    generate_user_archive_requests_pdf_file
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel


async def render_user_archive_request_identifier_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
):
    text = _get_user_archive_request_identifier_text()

    keyboard = [[ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]]

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


def _get_user_archive_request_identifier_text():
    return (
        "📕 <b>Archivio Richieste Utente</b>\n\n"
        "▫ Da qui puoi visionare l'archivio delle richieste di un utente.\n\n"
        "🔹 Fornisci un ID o uno username."
    )


# noinspection PyUnresolvedReferences
async def render_user_archive_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        user_id: int,
        requested_by_admin: bool = False
):
    requests = await get_user_requests_archive(user_id=user_id)

    text = await _get_user_request_archive_text(requests=requests, requested_from_admin=requested_by_admin)
    message_id = context.pydc.persistent.bot_message_id
    context.pydc.persistent.bot_message_id = None

    file = None
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
            if not message_id:
                raise
            await context.bot.edit_message_text(
                chat_id=update.effective_user.id,
                message_id=message_id,
                text=archive_text,
                parse_mode=ParseMode.HTML
            )
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        file = await _get_archive_pdf_file(requests=requests, user_id=user_id)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="🔙 Indietro", callback_key=base_path.back()),
                ButtonItem(
                    text="🏠 Home",
                    callback_key=PathBuilder(AdminRoute.ROOT if requested_by_admin else UserRoute.ROOT)
                )
            ]
        ],
        message_id=message_id
    )

    if file:
        assert isinstance(file, str)

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    text="🚮 Chiudi",
                    callback_data=GlobalAction.CLOSE_MENU
                )
            ]])
        )

        await delete_os_file(str(Path(file).with_suffix(".aux")))
        await delete_os_file(str(Path(file).with_suffix(".log")))
        await delete_os_file(str(Path(file).with_suffix(".out")))
        await delete_os_file(str(Path(file).with_suffix(".tex")))

        async def _delete_latex_file(context: CustomContext):
            await delete_os_file(path=file)

        job = context.job_queue.get_jobs_by_name("_delete_latex_file")
        if job:
            job[0].schedule_removal()
        context.job_queue.run_once(callback=_delete_latex_file, when=600)


async def _get_user_request_archive_text(requests: list[Request], requested_from_admin: bool = False) -> str:
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


async def _get_archive_pdf_file(requests: list[Request], user_id: int) -> str:
    if os.path.exists(f"archive_{user_id}_{len(requests)}.pdf"):
        return f"archive_{user_id}_{len(requests)}.pdf"

    file = await generate_user_archive_requests_pdf_file(
        requests=requests,
        input_path=f"archive_{user_id}_{len(requests)}.tex"
    )
    return file
