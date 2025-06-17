import asyncio
import os
from contextlib import nullcontext
from uuid import uuid4

import telegram.error
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from loggers import job_queue_logger


async def scheduled_delete_message(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    if "chat_id" not in data or "message_id" not in data:
        job_queue_logger.warn("'chat_id' or 'message_id' are missing in JobQueue data.")
        return
    try:
        await context.bot.delete_message(chat_id=data["chat_id"], message_id=data["message_id"])
    except telegram.error.TelegramError as e:
        job_queue_logger.warn(f'Not able to perform scheduled action: {e}')


async def scheduled_send_message(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    data = job.data
    send_media = data.get("media", {})

    if isinstance(send_media, dict):
        send_media = send_media.get("send", False)

    if not all(k in data for k in ("chat_id", "text")):
        job_queue_logger.warn("'chat_id' or 'text' are missing in JobQueue data.")
        return

    job_to_edit = next((j for j in context.bot_data["jobs"] if j == job.name), None)

    try:
        common_kwargs = {
            "chat_id": data["chat_id"],
            "reply_parameters": data.get("reply_parameters"),
            "reply_markup": data.get("reply_markup"),
            "message_thread_id": data.get("thread_id"),
            "parse_mode": "HTML"
        }

        if send_media:
            d = data["media"]["send"]
            if data["media"].get("send_as_document"):
                document = (open(d, "rb") if isinstance(d, str)
                            else d if not isinstance(d, (list, set, tuple, dict)) else d[0])
                async with document if hasattr(document, "__aenter__") else nullcontext(document) as doc:
                    message = await context.bot.send_document(
                        document=doc,
                        caption=data["text"],
                        **common_kwargs
                    )
                if "delete_after_sending" in data["media"]:
                    os.remove(d)
            else:
                message = await context.bot.send_media_group(
                    media=data["attachments"],
                    caption=data["text"],
                    **common_kwargs
                )
                d = data["media"]["send"]
                if not isinstance(d, (list, set, tuple, dict)):
                    message = message[0]
        else:
            message = await context.bot.send_message(
                text=data["text"],
                **common_kwargs
            )

        if job_to_edit:
            context.bot_data["jobs"][job_to_edit]["returned_value"] = message.id
            context.bot_data["jobs"][job_to_edit]["done"] = True

    except telegram.error.TelegramError as e:
        if job_to_edit:
            context.bot_data["jobs"].pop(job_to_edit, None)
        job_queue_logger.error(f'Not able to perform scheduled action: {e}')


async def scheduled_edit_message(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data

    if "chat_id" not in data or "message_id" not in data or "text" not in data:
        job_queue_logger.warn("'chat_id', 'message_id' or 'text' are missing in JobQueue data.")
        return

    chat_id = context.job.data["chat_id"]
    message_id = context.job.data["message_id"]
    text = context.job.data["text"]

    reply_markup = context.job.data["reply_markup"] if "reply_markup" in context.job.data else None

    try:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                                            reply_markup=reply_markup, parse_mode="HTML")
    except telegram.error.TelegramError as e:
        job_queue_logger.error(f'Not able to perform scheduled action: {e}')


async def send_temporary_message(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        additional_job_data=None,
        delay_before=2,
        delay_delete=10
):
    """
    Invia un messaggio temporaneo e lo elimina dopo un certo tempo.

    Args:
        update: L'oggetto update di Telegram.
        :param update:
        :param context: Il contesto della callback.
        :param text:
        :param delay_delete:
        :param delay_before:
        :param additional_job_data:
    """

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        message_thread_id=await get_thread_id(update),
        action=ChatAction.TYPING
    )

    job_id = str(uuid4())

    if additional_job_data is not None and "attachments" in additional_job_data and additional_job_data["attachments"]:
        media_bool = True
    else:
        media_bool = False

    job = context.job_queue.run_once(
        callback=scheduled_send_message,
        data={
            "chat_id": update.effective_chat.id,
            "thread_id": await get_thread_id(update),
            "text": text,
            "reply_markup": (additional_job_data["reply_markup"]
                             if additional_job_data is not None
                             and "reply_markup" in additional_job_data
                             else None),
            "media": media_bool
        },
        when=delay_before,
        name=job_id
    )

    context.bot_data["jobs"][job_id] = {
        "returned_value": None,
        "done": False
    }

    # Attendi il completamento del job
    while not context.bot_data["jobs"][job_id]["done"]:
        await asyncio.sleep(0.1)

    # Ottieni l'ID del messaggio restituito
    message_id = context.bot_data["jobs"][job_id]["returned_value"]

    # Rimuovi il job dalla lista
    context.bot_data["jobs"].pop(job_id, None)

    # Pianifica l'eliminazione del messaggio
    context.job_queue.run_once(
        callback=scheduled_delete_message,
        data={
            "chat_id": update.effective_chat.id,
            "message_id": message_id
        },
        when=delay_delete
    )


async def get_thread_id(update: Update):
    t_id = update.effective_message.message_thread_id
    if t_id is not None and t_id < 20:
        return t_id
    return None


