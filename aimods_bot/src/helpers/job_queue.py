import os
import asyncio
from typing import Optional, Any, Dict, cast, TypedDict, Literal
from uuid import uuid4

import telegram.error
from telegram import Update, InputMedia, InlineKeyboardMarkup, ReplyParameters
from telegram.constants import ChatAction, ParseMode

from aimods_bot.src.helpers.models.job_names import RemoveInactiveRequestJobName
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.utils import MediaItem
from aimods_bot.src.helpers.utils.bulk_sender import send_opening_notifications
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import JobDataMissingException, WrongTypeException
from aimods_bot.src.core.pydantic import JobInfo
from aimods_bot.src.helpers.models.jobs import ScheduledJobData, JobData, DeleteMessageJob, SendMessageJob, \
    EditMessageJob
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import get_file_type, normalize_files
from aimods_bot.src.helpers.utils.telegram_utils import get_valid_thread_id

log = logger.getChild(__name__)


async def async_remove_file(file_path: str):
    if os.path.exists(file_path):
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, os.remove, file_path)
            log.info(f"File Rimosso: {file_path}")
        except OSError as e:
            log.warning(f"Impossibile rimuovere {file_path}: {e}")


# ========== JOB: DELETE ==========

async def scheduled_delete_message(context: CustomContext):
    job = context.job
    if not job:
        raise ValueError("Attribute CustomContext.job must not be None here!")

    job_data = job.data
    if not isinstance(job_data, DeleteMessageJob):
        raise WrongTypeException(job_data, "job_data", "DeleteMessageJob")

    try:
        await context.bot.delete_message(
            chat_id=job_data.chat_id,
            message_id=job_data.message_id,
        )
        log.info(f"Message {job_data.message_id} deleted from {job_data.chat_id}")
    except telegram.error.BadRequest as e:
        if "not found" in str(e) or "deleted" in str(e):
            log.info(f"Message {job_data.message_id} already deleted.")
        else:
            log.warning(f"Delete error (Bad Request): {e}")
    except telegram.error.TelegramError as e:
        log.warning(f"Generic delete error: {e}")


# ========== JOB: SEND ==========

async def scheduled_send_message(context: CustomContext):
    job = context.job
    if not job:
        raise ValueError("Attribute CustomContext.job must not be None here!")

    job_name = job.name
    if not job_name:
        raise ValueError("Job must have a name!")

    job_data = job.data
    if not isinstance(job_data, SendMessageJob):
        raise WrongTypeException(job_data, "job_data", "SendMessageJob")

    if not job_data.text and not job_data.files:
        raise JobDataMissingException("Both 'job_data.text' and 'job_data.files' are empty; cannot send the message!")

    common_kwargs = {
        "chat_id": job_data.chat_id,
        "reply_parameters": job_data.reply_parameters,
        "message_thread_id": job_data.thread_id,
        "reply_markup": job_data.reply_markup,
        "parse_mode": ParseMode.HTML,
    }
    common_kwargs = {k: v for k, v in common_kwargs.items() if v is not None}

    try:
        if job_data.files:
            sent_obj = await _send_media_message(context=context, data_model=job_data, kwargs=common_kwargs)
            sent_messages = sent_obj if isinstance(sent_obj, list) else [sent_obj]
        elif job_data.text:
            msg = await context.bot.send_message(text=job_data.text, **common_kwargs)
            sent_messages = [msg]
        else:
            log.error("Nessun testo né media da inviare.")
            return

        if sent_messages and job_data.delete_after:
            job_queue = context.job_queue
            if not job_queue:
                raise ValueError("Attribute CustomContext.job_queue must not be None here!")

            msg_id = sent_messages[0].message_id
            job_queue.run_once(
                callback=scheduled_delete_message,
                when=job_data.delete_after,
                data=DeleteMessageJob(chat_id=job_data.chat_id, message_id=msg_id),
            )

        context.pydb.jobs.pop(job_name, None)
    except telegram.error.TelegramError as e:
        context.pydb.jobs.pop(job_name, None)
        log.error(f"Scheduled deliver error (chat: {job_data.chat_id}): {e}")


async def send_action_message_after(
    update: Update,
    context: CustomContext,
    text: str,
    recipient_id: Optional[int] = None,
    time: int = 1,
    files: Optional[list[InputMedia | str]] = None,
    send_as_document: bool = False,
    delete_after_sending: bool = False,
    thread_id: Optional[int] = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    reply_parameters: Optional[ReplyParameters] = None,
    delete_after: Optional[int] = None,
):
    """Invia un messaggio dopo un certo tempo, mostrando prima l'azione di scrittura o upload."""
    recipient = recipient_id or update.effective_chat.id
    resolved_thread_id = thread_id if thread_id is not None else get_valid_thread_id(update)

    job_data = SendMessageJob(
        chat_id=recipient,
        text=text,
        files=files or [],
        send_as_document=send_as_document,
        delete_after_sending=delete_after_sending,
        thread_id=resolved_thread_id,
        reply_markup=reply_markup,
        reply_parameters=reply_parameters,
        delete_after=delete_after,
    )

    await context.bot.send_chat_action(
        chat_id=recipient,
        message_thread_id=resolved_thread_id,
        action=ChatAction.UPLOAD_DOCUMENT if files else ChatAction.TYPING,
    )

    job_id = str(uuid4())
    job = context.job_queue.run_once(
        callback=scheduled_send_message,
        data=job_data,
        when=time,
        name=job_id,
    )

    context.pydb.jobs[job_id] = JobInfo(next_date=job.next_t)


async def _send_media_message(
    context: CustomContext,
    job_data: SendMessageJob,
    kwargs: Dict[str, Any],
):
    raw_files = job_data.files
    as_doc = job_data.send_as_document

    media_items = [
        MediaItem(item=el, type=get_file_type(el), as_doc=as_doc)
        for el in raw_files
    ]

    normalized_media = await normalize_files(media_items)

    try:
        if len(normalized_media) == 1:
            ftype, input_media = normalized_media[0]
            result_message = await _send_single_media(
                context=context,
                item=(ftype, input_media),
                caption=job_data.text,
                kwargs=kwargs,
                as_doc=as_doc,
            )
        else:
            result_message = await _send_media_group(
                context=context,
                items=normalized_media,
                caption=job_data.text,
                local_kwargs=kwargs,
            )
    finally:
        if job_data.delete_after_sending:
            await asyncio.gather(
                *(async_remove_file(f) for f in raw_files if isinstance(f, str))
            )

    return result_message


async def _send_single_media(
        context: CustomContext,
        item: tuple[Literal["document", "photo", "audio", "video", "gif"], InputMedia],
        caption: str | None,
        kwargs: Dict[str, Any],
        as_doc: bool
):
    ftype, input_file = item
    media = input_file.media

    local_kwargs = kwargs.copy()
    local_kwargs['caption'] = caption

    if as_doc or ftype == "document":
        return await context.bot.send_document(document=media, **local_kwargs)

    method_map = {
        "photo": context.bot.send_photo,
        "audio": context.bot.send_audio,
        "video": context.bot.send_video,
        "gif": context.bot.send_animation,
    }

    method = method_map.get(ftype, context.bot.send_document)
    param_name = ftype if ftype in ["photo", "audio", "video"] else ("animation" if ftype == "gif" else "document")

    local_kwargs[param_name] = media
    return await method(**local_kwargs)


async def _send_media_group(
        context: CustomContext,
        items: list[tuple[Literal["document", "photo", "audio", "video", "gif"], InputMedia]],
        caption: str | None,
        local_kwargs: Dict[str, Any]
):
    local_kwargs.pop("reply_markup", None)

    media_list = [el[1].media for el in items]

    messages = await context.bot.send_media_group(media=media_list, caption=caption, **local_kwargs)

    return messages[0]  # send_media_group ritorna sempre una tupla


# ========== JOB: EDIT ==========

async def scheduled_edit_message(context: CustomContext):
    job_data = context.job.data
    if not isinstance(job_data, EditMessageJob):
        raise WrongTypeException(job_data, "job_data", "EditMessageJob")

    try:
        await context.bot.edit_message_text(
            chat_id=job_data.chat_id,
            message_id=job_data.message_id,
            text=job_data.text,
            reply_markup=job_data.reply_markup,
            parse_mode=ParseMode.HTML,
        )
        log.info(f"Message {job_data.message_id} edited in {job_data.chat_id}")
    except telegram.error.BadRequest as e:
        if "Message was not edited" in str(e):
            log.info(f"Message {job_data.message_id} not edited: contents were identical.")
        else:
            log.error(f"Edit error (Bad Request): {e}")
    except telegram.error.TelegramError as e:
        log.error(f"Generic delete error: {e}")


async def send_temporary_message(
    update: Update,
    context: CustomContext,
    text: str,
    recipient_id: Optional[int],
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    thread_id: Optional[int] = None,
    delay_before: int = 2,
    delay_delete: int = 10,
):
    """Invia un messaggio temporaneo che viene eliminato dopo un certo tempo."""
    chat_id = recipient_id or update.effective_chat.id
    resolved_thread_id = thread_id if thread_id is not None else get_valid_thread_id(update)

    await context.bot.send_chat_action(
        chat_id=chat_id,
        message_thread_id=resolved_thread_id,
        action=ChatAction.TYPING,
    )

    job_data = SendMessageJob(
        chat_id=chat_id,
        text=text,
        thread_id=resolved_thread_id,
        reply_markup=reply_markup,
        delete_after=delay_delete,
    )

    context.job_queue.run_once(
        callback=scheduled_send_message,
        when=delay_before,
        data=job_data,
    )

        
# ========== JOB: REQUESTS ==========

async def scheduled_remove_completed_requests(context: CustomContext):
    data = context.job.data
    if not isinstance(data, dict) or "request_id" not in data:
        raise JobDataMissingException("Request ID not provided!")

    request_id = int(data["request_id"])
    context.remove_from_active_requests(ix=request_id)

    job_name = str(RemoveInactiveRequestJobName(request_id=request_id))
    context.pydb.jobs.pop(job_name, None)


async def scheduled_remove_user_request_cooldown(context: CustomContext):
    data = context.job.data
    if not isinstance(data, dict) or "user_id" not in data:
        raise JobDataMissingException("User ID not provided!")

    context.remove_user_request_cooldown(user_id=int(data["user_id"]))


# ========== JOB: LIMITATIONS ==========


class RemoveLimitJobData(TypedDict):
    user_id: int
    section: RequestSection  # es. "windows:game"


async def scheduled_remove_user_request_section_limitation(context: CustomContext):
    """Rimuove la limitazione (utente, sezione) scaduta."""
    data: RemoveLimitJobData = context.job.data
    user_id = data["user_id"]
    section = data["section"]

    current = context.get_user_request_limitations(user_id=user_id)
    if not current:
        return

    remaining = [
        x for x in current
        if not (x.section.platform == section.platform and x.section.category == section.category)
    ]
    context.set_user_request_limitations(user_id=user_id, limitations=remaining)


# ========== JOB: SECTIONS MANAGEMENT ==========


class SectionOpeningCheckJobData(TypedDict):
    section: RequestSection


async def scheduled_section_opening_check_for_user_notification(context: CustomContext):
    if not context.job or not context.job.data:
        raise ValueError("Job o job data mancanti!")

    data: SectionOpeningCheckJobData = context.job.data
    section = data["section"]

    if context.is_request_section_open(section=section):
        await send_opening_notifications(context=context, section=section)
