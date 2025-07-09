import asyncio
import os
from contextlib import nullcontext
from uuid import uuid4
from typing import Optional

import telegram.error
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.core.exceptions import JobDataMissingException

log = logger.getChild("job_queue")


# ========== UTILITÀ ==========

def get_valid_thread_id(update: Update) -> Optional[int]:
    thread_id = update.effective_message.message_thread_id
    if thread_id is not None and thread_id < 20:
        return thread_id
    return None


def register_job(context, job_id: str):
    context.bot_data.setdefault("jobs", {})
    context.bot_data["jobs"][job_id] = {"returned_value": None, "done": False}


def mark_job_done(context, job_id: str, message_id: int):
    context.bot_data["jobs"][job_id]["returned_value"] = message_id
    context.bot_data["jobs"][job_id]["done"] = True


# ========== JOB: DELETE ==========

async def scheduled_delete_message(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    if "chat_id" not in data or "message_id" not in data:
        raise JobDataMissingException("Dati mancanti: 'chat_id' o 'message_id'")

    try:
        await context.bot.delete_message(
            chat_id=data["chat_id"],
            message_id=data["message_id"]
        )
        log.info(f"🗑️ Messaggio {data['message_id']} eliminato da {data['chat_id']}")
    except telegram.error.TelegramError as e:
        log.warning(f"⚠️ Errore nell'eliminazione programmata: {e}")


# ========== JOB: SEND ==========

async def scheduled_send_message(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    data = job.data
    send_media = data.get("media", {}).get("send", False) if isinstance(data.get("media"), dict) else False

    if "chat_id" not in data or "text" not in data:
        raise JobDataMissingException("Dati mancanti: 'chat_id' o 'text'")

    job_to_edit = next((j for j in context.bot_data["jobs"] if j == job.name), None)

    common_kwargs = {
        "chat_id": data["chat_id"],
        "reply_parameters": data.get("reply_parameters"),
        "reply_markup": data.get("reply_markup"),
        "message_thread_id": data.get("thread_id"),
        "parse_mode": "HTML"
    }

    try:
        if send_media:
            message = await _send_media_message(context, data, common_kwargs)
        else:
            message = await context.bot.send_message(
                text=data["text"],
                **common_kwargs
            )
        if job_to_edit:
            mark_job_done(context, job_to_edit, message.message_id)
    except telegram.error.TelegramError as e:
        if job_to_edit:
            context.bot_data["jobs"].pop(job_to_edit, None)
        log.error(f"❌ Errore nell'invio programmato: {e}")


async def _send_media_message(context, data, kwargs):
    d = data["media"]["send"]
    if data["media"].get("send_as_document"):
        document = open(d, "rb") if isinstance(d, str) else d if not isinstance(d, (list, set, tuple, dict)) else d[0]
        async with document if hasattr(document, "__aenter__") else nullcontext(document) as doc:
            message = await context.bot.send_document(
                document=doc,
                caption=data["text"],
                **kwargs
            )
        if data["media"].get("delete_after_sending") and isinstance(d, str):
            os.remove(d)
        return message
    else:
        message = await context.bot.send_media_group(
            media=data["attachments"],
            caption=data["text"],
            **kwargs
        )
        if not isinstance(data["media"]["send"], (list, set, tuple, dict)):
            message = message[0]
        return message


# ========== JOB: EDIT ==========

async def scheduled_edit_message(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    if not all(k in data for k in ("chat_id", "message_id", "text")):
        raise JobDataMissingException("Dati mancanti: 'chat_id' o 'message_id' o 'text'")

    try:
        await context.bot.edit_message_text(
            chat_id=data["chat_id"],
            message_id=data["message_id"],
            text=data["text"],
            reply_markup=data.get("reply_markup"),
            parse_mode="HTML"
        )
        log.info(f"✏️ Messaggio modificato in {data['chat_id']}")
    except telegram.error.TelegramError as e:
        log.error(f"❌ Errore durante la modifica del messaggio: {e}")


async def send_temporary_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    additional_job_data: Optional[dict] = None,
    delay_before: int = 2,
    delay_delete: int = 10
):
    """
    Invia un messaggio temporaneo che viene eliminato dopo un certo tempo.
    """

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        message_thread_id=get_valid_thread_id(update),
        action=ChatAction.TYPING
    )

    job_id = str(uuid4())
    media_bool = additional_job_data.get("media", False) if additional_job_data else False

    context.job_queue.run_once(
        callback=scheduled_send_message,
        when=delay_before,
        name=job_id,
        data={
            "chat_id": update.effective_chat.id,
            "thread_id": get_valid_thread_id(update),
            "text": text,
            "reply_markup": additional_job_data.get("reply_markup") if additional_job_data else None,
            "media": additional_job_data if media_bool else False
        }
    )

    register_job(context, job_id)
    await _wait_for_job_completion(context, job_id)

    message_id = context.bot_data["jobs"][job_id]["returned_value"]
    context.bot_data["jobs"].pop(job_id, None)

    context.job_queue.run_once(
        callback=scheduled_delete_message,
        when=delay_delete,
        data={"chat_id": update.effective_chat.id, "message_id": message_id}
    )


async def _wait_for_job_completion(context, job_id: str):
    while not context.bot_data["jobs"][job_id]["done"]:
        await asyncio.sleep(0.1)
