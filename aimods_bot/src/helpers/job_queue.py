import os
import asyncio
from typing import Optional, Any, Dict, cast, TypedDict, Literal
from uuid import uuid4

import telegram.error
from telegram import Update, InputMedia
from telegram.constants import ChatAction, ParseMode

from aimods_bot.src.helpers.utils.bulk_sender import send_opening_notifications
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import JobDataMissingException, WrongTypeException
from aimods_bot.src.core.pydantic import JobInfo
from aimods_bot.src.helpers.constants.models import ScheduledJobData, JobData, MediaItem
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
    data = context.job.data

    if not isinstance(data, ScheduledJobData):
        raise WrongTypeException(data, "data", "ScheduledJobData")

    chat_id = data.chat_id
    message_id = data.additional_data.message_id

    if not data.chat_id or not data.additional_data.message_id:
        raise JobDataMissingException("Dati mancanti: 'chat_id' o 'message_id'")

    try:
        await context.bot.delete_message(chat_id=data.chat_id, message_id=message_id)
        log.info(f'Messaggio {message_id} eliminato da {chat_id}')
    except telegram.error.BadRequest as e:
        if "not found" in str(e) or "deleted" in str(e):
            log.info(f"Messaggio {message_id} già eliminato.")
        else:
            log.warning(f"Errore delete (Bad Request): {e}")
    except telegram.error.TelegramError as e:
        log.warning(f"Errore delete generico: {e}")


# ========== JOB: SEND ==========

async def scheduled_send_message(context: CustomContext):
    job = context.job
    data_model = job.data

    if not isinstance(data_model, ScheduledJobData):
        raise WrongTypeException(data_model, "data_model", "ScheduledJobData")

    additional_data = data_model.additional_data or JobData()
    file_paths = additional_data.files

    send_media = additional_data.files is not None

    if (not data_model.text and not send_media) or not data_model.chat_id:
        raise JobDataMissingException("Dati mancanti: 'chat_id' o 'text'")

    common_kwargs = {
        "chat_id": data_model.chat_id,
        "reply_parameters": additional_data.reply_parameters,
        "message_thread_id": additional_data.thread_id,
        "reply_markup": additional_data.reply_markup,
        "parse_mode": ParseMode.HTML
    }

    common_kwargs = {k: v for k, v in common_kwargs.items() if v is not None}

    try:
        if file_paths:
            sent_obj = await _send_media_message(context, data_model, common_kwargs)
            sent_messages = sent_obj if isinstance(sent_obj, list) else [sent_obj]
        elif data_model.text:
            msg = await context.bot.send_message(text=data_model.text, **common_kwargs)
            sent_messages = [msg]
        else:
            log.error("Nessun testo né media da inviare.")
            return

        if sent_messages and additional_data.delete_after:
            msg_id = sent_messages[0].message_id

            context.job_queue.run_once(
                callback=scheduled_delete_message,
                when=additional_data.delete_after,
                data=ScheduledJobData(
                    chat_id=data_model.chat_id,
                    additional_data=JobData(message_id=msg_id)
                )
            )

        if job.name in context.pydb.jobs:
            del context.pydb.jobs[job.name]
    except telegram.error.TelegramError as e:
        job_key = job.name
        if job_key in context.pydb.jobs:
            context.pydb.jobs.pop(job_key, None)
        log.error(f"Errore invio programmato (Chat: {data_model.chat_id}): {e}")


async def send_action_message_after(update: Update,
                                    context: CustomContext,
                                    text: str,
                                    recipient_id: Optional[int] = None,
                                    time: int = 1,
                                    additional_job_data: Optional[JobData] = None):
    """
        Invia un messaggio dopo un certo tempo, mostrando prima l'azione di scrittura o upload.
    """

    thread_id = additional_job_data.thread_id if additional_job_data else get_valid_thread_id(update)
    recipient = recipient_id or update.effective_chat.id

    job_data = ScheduledJobData(
        text=text,
        chat_id=recipient,
        additional_data=additional_job_data
    )

    await context.bot.send_chat_action(
        chat_id=recipient,
        message_thread_id=thread_id,
        action=ChatAction.UPLOAD_DOCUMENT if additional_job_data.files else ChatAction.TYPING
    )

    job_id = str(uuid4())
    context.job_queue.run_once(
        callback=scheduled_send_message,
        data=job_data,
        when=time,
        name=job_id
    )

    context.pydb.jobs[job_id] = JobInfo()


async def _send_media_message(context: CustomContext, data_model: ScheduledJobData, kwargs: Dict[str, Any]):
    additional_data = data_model.additional_data
    raw_files = additional_data.files
    as_doc = additional_data.send_as_document

    if isinstance(raw_files, str):
        raw_files = [raw_files]

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
                caption=data_model.text,
                kwargs=kwargs,
                as_doc=as_doc
            )
        else:
            result_message = await _send_media_group(
                context=context,
                items=normalized_media,
                caption=data_model.text,
                local_kwargs=kwargs
            )
    finally:
        if additional_data.delete_after_sending:
            await asyncio.gather(*(async_remove_file(f) for f in raw_files if isinstance(f, str)))

    return result_message


async def _send_single_media(
        context: CustomContext,
        item: tuple[Literal["document", "photo", "audio", "video", "gif"], InputMedia],
        caption: str,
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
        caption: str,
        local_kwargs: Dict[str, Any]
):
    local_kwargs.pop("reply_markup", None)

    media_list = [el[1].media for el in items]

    messages = await context.bot.send_media_group(media=media_list, caption=caption, **local_kwargs)

    return messages[0]  # send_media_group ritorna sempre una tupla


# ========== JOB: EDIT ==========

async def scheduled_edit_message(context: CustomContext):
    data = cast(ScheduledJobData, context.job.data)
    text = data.text
    chat_id = data.chat_id
    message_id = data.additional_data.message_id
    additional_job_data = data.additional_data
    reply_markup = additional_job_data.reply_markup if additional_job_data and additional_job_data.reply_markup else None

    if not isinstance(data, ScheduledJobData):
        raise WrongTypeException(data, "data", "ScheduledJobData")
    if not text or not chat_id or not message_id:
        raise JobDataMissingException("Dati mancanti: 'chat_id' o 'message_id' o 'text'")

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        log.info(f"Messaggio modificato in {chat_id}")
    except telegram.error.BadRequest as e:
        if "Message is not modified" in str(e):
            log.info(f"Messaggio {message_id} non modificato (contenuto identico).")
        else:
            log.error(f"Errore BadRequest edit: {e}")
    except telegram.error.TelegramError as e:
        log.error(f"Errore durante la modifica del messaggio: {e}")


async def send_temporary_message(
    update: Update,
    context: CustomContext,
    text: str,
    recipient_id: Optional[int],
    additional_job_data: Optional[JobData] = None,
    delay_before: int = 2,
    delay_delete: int = 10
):
    """
    Invia un messaggio temporaneo che viene eliminato dopo un certo tempo.
    """

    chat_id = recipient_id if recipient_id else update.effective_chat.id
    thread_id = get_valid_thread_id(update)

    await context.bot.send_chat_action(
        chat_id=chat_id,
        message_thread_id=thread_id,
        action=ChatAction.TYPING
    )

    if additional_job_data is None:
        additional_job_data = JobData()

    additional_job_data.delete_after = delay_delete

    if not additional_job_data.thread_id:
        additional_job_data.thread_id = thread_id

    job_data = ScheduledJobData(
        chat_id=chat_id,
        text=text,
        additional_data=additional_job_data
    )

    context.job_queue.run_once(
        callback=scheduled_send_message,
        when=delay_before,
        data=job_data
    )

        
# ========== JOB: REQUESTS ==========

async def scheduled_remove_completed_requests(context: CustomContext):
    data = cast(dict, context.job.data)
    if "ix" not in data:
        raise JobDataMissingException("Dato mancante: 'ix'")

    ix = int(data["ix"])
    context.remove_from_active_requests(ix=ix)
    try:
        del context.pydb.jobs[f"remove_inactive_request:{ix}"]
    except KeyError:
        pass


async def scheduled_remove_request_cooldown(context: CustomContext):
    data = context.job.data

    if "user_id" not in data:
        raise JobDataMissingException("Cannot remove request cooldown without a user_id.")

    context.remove_user_request_cooldown(user_id=int(data["user_id"]))


# ========== JOB: LIMITATIONS ==========


class RemoveLimitJobData(TypedDict):
    user_id: int
    section: str  # es. "windows:game"


async def scheduled_remove_user_request_section_limitation(context: CustomContext):
    """Esegue la rimozione programmata di una limitazione sulle richieste (utente e sezione indicati)"""
    data: RemoveLimitJobData = context.job.data
    user_id = data["user_id"]
    section = data["section"]

    current = context.get_user_request_limitations(user_id=user_id)
    remaining = [x for x in current if x.section != section]
    context.set_user_request_limitations(user_id=user_id, limitations=remaining)


# ========== JOB: SECTIONS MANAGEMENT ==========

async def scheduled_section_opening_check_for_user_notification(context: CustomContext):
    if not context.job:
        raise ValueError("Job must not be None!")

    if not context.job.data:
        raise ValueError("Job data must not be None!")

    if not isinstance(context.job.data, dict):
        raise ValueError("Job data must be a dict!")

    if any(dict_item not in context.job.data for dict_item in ("platform", "category")):
        raise ValueError("Missing platform or category in job data!")

    platform, category = context.job.data["platform"], context.job.data["category"]

    if context.is_request_section_open(platform=platform, category=category):
        await send_opening_notifications(context=context, platform=platform, category=category)
