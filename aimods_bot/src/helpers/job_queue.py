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
        log.error("❗ 'chat_id' o 'message_id' mancanti nei dati del job.")
        return

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
        log.warning("❗ 'chat_id', 'message_id' o 'text' mancano nel job.")
        return

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
