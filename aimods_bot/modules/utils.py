import json
import re
from datetime import timedelta
from uuid import uuid4

import telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from aimods_bot.modules import job_queue_functions
from aimods_bot.modules.exceptions import AlertException
from aimods_bot.modules.loggers import bot_logger


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
                "thread_id": await get_thread_id(update),
                "reply_markup": InlineKeyboardMarkup(keyboard)
            }
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=await get_thread_id(update),
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

    if additional_job_data and "thread_id" in additional_job_data:
        t_id = additional_job_data["thread_id"]
    else:
        t_id = await get_thread_id(update)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                       message_thread_id=t_id,
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


async def parse_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    pattern = r"[/.!](\w+)\s*(?:(@\w+|(\d{7,})|<a\s+href=\"tg://user\?id=(\d{7,})\">.*?</a>))?\s*((?:\d+\s*(?:giorni|ore|minuti|secondi)\s*)*)\s*(.*)?"
    match = re.match(pattern, command)

    if not match:
        bot_logger.error(f"Invalid command: {command}")
        await send_private_alert(
            update=update,
            context=context,
            text="⚠️ Warning\n\nLa sintassi del comando non è corretta."
        )
        # potremmo in qualche modo linkare un manuale di utilizzo
        return None

    action = match.group(1)  # Comando (ban, mute, warn, ecc.)
    username = match.group(2)  # Può essere @username o None
    user_id = match.group(3) or match.group(4)  # ID numerico (da input diretto o da menzione HTML)
    user = user_id if user_id else username  # Se c'è un ID, usiamo quello, altrimenti username
    duration_text = match.group(5) or ""  # Durata
    message = match.group(6) or ""  # Messaggio

    duration_mapping = {"giorni": "days", "ore": "hours", "minuti": "minutes", "secondi": "seconds"}
    duration_kwargs = {key: 0 for key in duration_mapping.values()}

    for num, unit in re.findall(r"(\d+)\s*(giorni|ore|minuti|secondi)", duration_text):
        duration_kwargs[duration_mapping[unit]] = int(num)

    duration = timedelta(**duration_kwargs) if any(duration_kwargs.values()) else None

    return {
        "action": action,
        "user": user,
        "duration": duration,
        "message": message.strip() if message else None
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


async def get_thread_id(update: Update):
    t_id = update.effective_message.message_thread_id
    if t_id is not None and t_id < 20:
        return t_id
    return None
