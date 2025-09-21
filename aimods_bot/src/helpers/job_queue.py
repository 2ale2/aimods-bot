import asyncio
import os
from typing import Optional, Any, Dict, cast, TypedDict
from uuid import uuid4

import telegram.error
from telegram import Update
from telegram.constants import ChatAction

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import JobDataMissingException, WrongTypeException
from aimods_bot.src.helpers.constants.models import ScheduledJobData, JobData, MediaItem
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import get_file_type, normalize_files
from aimods_bot.src.helpers.utils.telegram_utils import get_valid_thread_id

log = logger.getChild("job_queue")


# ========== UTILITÀ ==========

def register_job(context, job_id: str):
    context.bot_data.setdefault("jobs", {})
    context.bot_data["jobs"][job_id] = {"returned_value": None, "done": False}


def mark_job_done(context, job_id: str, message_id: int):
    context.bot_data["jobs"][job_id]["returned_value"] = message_id
    context.bot_data["jobs"][job_id]["done"] = True


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
        await context.bot.delete_message(
            chat_id=data.chat_id,
            message_id=data.additional_data.message_id
        )
        log.info(f"🗑️ Messaggio {message_id} eliminato da {chat_id}")
    except telegram.error.TelegramError as e:
        log.warning(f"⚠️ Errore nell'eliminazione programmata: {e}")


# ========== JOB: SEND ==========

async def scheduled_send_message(context: CustomContext):
    job = context.job
    data_model = job.data

    if not isinstance(data_model, ScheduledJobData):
        raise WrongTypeException(data_model, "data_model", "ScheduledJobData")

    additional_data = data_model.additional_data

    send_media = additional_data and additional_data.files is not None

    if (not data_model.text and not send_media) or not data_model.chat_id:
        raise JobDataMissingException("Dati mancanti: 'chat_id' o 'text'")

    job_to_edit = next((j for j in context.bot_data["jobs"] if j == job.name), None)

    common_kwargs = {
        "chat_id": data_model.chat_id,
        "reply_parameters": additional_data.reply_parameters if additional_data else None,
        "message_thread_id": additional_data.thread_id if additional_data else None,
        "reply_markup": additional_data.reply_markup if additional_data else None,
        "parse_mode": "HTML"
    }

    try:
        if send_media:
            message = await _send_media_message(context, data_model, common_kwargs)
        else:
            message = await context.bot.send_message(
                text=data_model.text,
                **common_kwargs
            )
        if job_to_edit:
            if isinstance(message, tuple):
                message = message[0]
            mark_job_done(context, job_to_edit, message.message_id)
    except telegram.error.TelegramError as e:
        if job_to_edit:
            context.bot_data["jobs"].pop(job_to_edit, None)
        log.error(f"❌ Errore nell'invio programmato: {e}")


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

    context.bot_data.setdefault("jobs", {})
    context.bot_data["jobs"][job_id] = {
        "returned_value": None,
        "done": False
    }


async def _send_media_message(context: CustomContext, data_model: ScheduledJobData, kwargs: Dict[str, Any]):
    d_media = data_model.additional_data
    d = d_media.files
    as_doc = d_media.send_as_document
    if isinstance(d, str):
        d = [d]
    l = [MediaItem(item=el, type=get_file_type(el), as_doc=as_doc) for el in d]
    normalized_l = await normalize_files(l)
    if len(normalized_l) == 1:
        # normalized_l = [(tipo, input_media), ...]
        item = normalized_l[0]
        file = item[1]
        ftype = item[0]
        text = data_model.text
        if as_doc or ftype == "document":
            message = await context.bot.send_document(
                document=file.media,
                caption=text,
                **kwargs
            )
            if d_media.delete_after_sending and isinstance(d_media.files, str):
                try:
                    os.remove(d_media.files)
                    log.warning()
                except Exception as e:
                    log.warning(f"Non è stato possibile rimuovere il file: {e}")
                    pass
            return message
        else:
            file = file.media
            match ftype:
                case "photo":
                    await context.bot.send_photo(
                        photo=file,
                        caption=text,
                        **kwargs
                    )
                case "audio":
                    await context.bot.send_audio(
                        audio=file,
                        caption=text,
                        **kwargs
                    )
                case "video":
                    await context.bot.send_video(
                        video=file,
                        caption=text,
                        **kwargs
                    )
                case _:  # GIF
                    await context.bot.send_animation(
                        animation=file,
                        caption=text,
                        **kwargs
                    )
    else:
        if "reply_markup" in kwargs:
            del kwargs["reply_markup"]
        # noinspection PyTypeChecker
        message = await context.bot.send_media_group(
            media=[el[1].media for el in normalized_l],
            caption=data_model.text,
            **kwargs
        )
        if not isinstance(d, (list, set, tuple, dict)):
            message = message[0]
        return message


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
            parse_mode="HTML"
        )
        log.info(f"✏️ Messaggio modificato in {chat_id}")
    except telegram.error.TelegramError as e:
        log.error(f"❌ Errore durante la modifica del messaggio: {e}")


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

    job_id = str(uuid4())

    job_data = ScheduledJobData(
        chat_id=chat_id,
        text=text,
        additional_data=additional_job_data
    )

    context.job_queue.run_once(
        callback=scheduled_send_message,
        when=delay_before,
        name=job_id,
        data=job_data
    )

    register_job(context, job_id)
    await _wait_for_job_completion(context, job_id)

    message_id = context.bot_data["jobs"][job_id]["returned_value"]
    context.bot_data["jobs"].pop(job_id, None)

    context.job_queue.run_once(
        callback=scheduled_delete_message,
        when=delay_delete,
        data=ScheduledJobData(
            chat_id=chat_id,
            text=None,
            additional_data=JobData(
                message_id=message_id
            )
        )
    )


async def _wait_for_job_completion(context: CustomContext, job_id: str):
    while not context.pyd.jobs[job_id].executed:
        await asyncio.sleep(0.1)
        
# ========== JOB: REQUESTS ==========

async def scheduled_remove_completed_requests(context: CustomContext):
    data = cast(dict, context.job.data)
    if "ix" not in data:
        raise JobDataMissingException("Dato mancante: 'ix'")

    context.remove_from_active_requests(ix=int(data["ix"]))


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
