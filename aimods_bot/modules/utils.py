import json
import os
from uuid import uuid4

import psycopg
import telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from aimods_bot.modules.exceptions import AlertException
from aimods_bot.modules.loggers import db_logger, bot_logger
from aimods_bot.modules import job_queue_functions


async def delete_effective_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id
        )
    except telegram.error.BadRequest:
        pass


async def send_private_alert(update: Update,
                             context: ContextTypes.DEFAULT_TYPE,
                             text: str,
                             button_text="Open It Privately 💬",
                             delay=2):
    """
        Invia un messaggio privato in una chat pubblica apribile solo dal destinatario.

        Args:
            text (str): Il testo del messaggio di alert.
            button_text (str): Il testo del pulsante inline (default: "Open It Privately 💬").
            delay (int): Tempo in secondi prima di inviare il messaggio (default: 2s).
    """

    if "alerts" not in context.user_data:
        context.user_data["alerts"] = {}

    alert_id = str(uuid4())
    context.user_data["alerts"][alert_id] = text

    keyboard = [
        [
            InlineKeyboardButton(
                button_text,
                callback_data=f"alert_{update.effective_user.id}_{alert_id}"
            )
        ]
    ]

    if delay > 0:
        await send_action_message_after(
            update=update,
            context=context,
            text=f"🔐 Message for {update.effective_user.name}",
            time=delay,
            additional_job_data={
                "thread_id": update.effective_message.message_thread_id,
                "reply_markup": InlineKeyboardMarkup(keyboard)
            }
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=update.effective_message.message_thread_id,
            text=f"🔐 Message for {update.effective_user.name}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def open_private_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apre un alert privato per un utente."""

    infos = update.callback_query.data.split("_")
    if len(infos) != 3:
        raise AlertException()

    recipient = int(infos[1])
    alert_id = infos[2]

    if update.effective_user.id != recipient:
        return

    if "alerts" in context.user_data:
        for alert in context.user_data["alerts"]:
            if alert == alert_id:
                text = context.user_data["alerts"][alert]
                await update.callback_query.answer(
                    text=text,
                    show_alert=True
                )
                context.user_data["alerts"].pop(alert, None)
                break
    try:
        await update.effective_message.delete()
    except telegram.error.BadRequest:
        pass


async def send_action_message_after(update: Update,
                                    context: ContextTypes.DEFAULT_TYPE,
                                    text: str,
                                    recipient_id=None,
                                    time=1,
                                    additional_job_data=None):
    """Invia un messaggio dopo un tempo specificato, simulando l'azione di scrittura (max 5 secondi)."""

    await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                       message_thread_id=update.effective_message.message_thread_id if update.effective_message.message_thread_id else None,
                                       action=ChatAction.TYPING)

    job_data = (additional_job_data if additional_job_data is not None else {}) | {
        "text": text,
        "chat_id": recipient_id if recipient_id is not None else update.effective_chat.id,
    }

    job_id = str(uuid4())
    job = context.job_queue.run_once(
        callback=job_queue_functions.scheduled_send_message,
        data=job_data,
        when=time,
        name=job_id
    )
    context.bot_data["jobs"][job_id] = {
        "job": job,
        "returned_value": None,
        "done": False
    }


def get_data_from_json(data: str):
    """
    :return:    il contenuto del file di configurazione json richiesto
    """
    with open("aimods_bot/misc/data.json", encoding="utf-8", mode="r") as fp:
        content = json.load(fp)
        try:
            return content[data]
        except KeyError as e:
            bot_logger.error(f"Chiave {e} mancante in 'data.json'")
            raise KeyError(e)


async def get_file(file):
    try:
        iter(file)
    except TypeError:
        return file.get_file()
    else:
        await get_file(file[-1])


def connect_to_database():
    try:
        conn = psycopg.connect(os.getenv("POSTGRES_CONNECTION_URL"), client_encoding="utf8")
    except psycopg.Error as e:
        db_logger.error(f'Unable to access database: {e}')
        raise psycopg.Error(f'Unable to access database: {e}')
    return conn

