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
from aimods_bot.modules.database_functions import execute_query


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


async def parse_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str, full_command: str):
    pattern = context.bot_data["commands"][command]["pattern"]
    parameters = context.bot_data["commands"][command]["parameters"]

    match = re.match(pattern, full_command)

    if not match:
        bot_logger.error(f"Invalid command: {full_command}")
        await send_private_alert(
            update=update,
            context=context,
            text="⚠️ Warning\n\n▪️ La sintassi del comando non è corretta."
        )
        # potremmo in qualche modo linkare un manuale di utilizzo
        return None

    extracted = {"action": match.group(1)}
    gidx = 2
    for param in parameters:
        if param == "mention":
            username = match.group(gidx)  # Può essere @username o None
            user_id = match.group(gidx + 1) or match.group(gidx + 2)  # ID (da input diretto o da menzione HTML)
            extracted["user"] = user_id if user_id else username  # Se c'è un ID, usiamo quello, altrimenti username
            gidx += 3
        elif param == "permissions":
            extracted["permissions"] = [pe for pe in [int(p) for p in match.group(gidx).split(",")] if pe <= 11]
            gidx += 1
        else:
            if param == "duration" or param == "message":
                extracted[param] = match.group(gidx) or ""
            else:
                extracted[param] = match.group(gidx)
            gidx += 1

    duration_mapping = {
        "giorno": "days", "giorni": "days",
        "ora": "hours", "ore": "hours",
        "minuto": "minutes", "minuti": "minutes",
        "secondo": "seconds", "secondi": "seconds"
    }

    duration_kwargs = {key: 0 for key in duration_mapping.values()}  # ← Questa serve

    if "duration" in extracted:
        for num, unit in re.findall(r"(\d+)\s*(giorni|giorno|ore|ora|minuti|minuto|secondi|secondo)",
                                    extracted["duration"]):
            duration_kwargs[duration_mapping[unit]] += int(num)

        extracted["duration"] = timedelta(**duration_kwargs) if any(duration_kwargs.values()) else None

    parsed = {}
    for el in extracted:
        if el == "message":
            parsed[el] = extracted[el].strip() if extracted[el] else None
        parsed[el] = extracted[el]

    return {
        "action": extracted["action"],
        "user": extracted["user"] if "user" in extracted else None,
        "duration": extracted["duration"] if "duration" in extracted else "",
        "message": extracted["message"] if "message" in extracted else None,
        "permissions": extracted["permissions"] if "permissions" in extracted else None,
    }


async def get_user_warnings(user_id: int):
    query = (f"SELECT COUNT(*) FROM warnings WHERE user_id = {user_id} "
             f"AND (expires_at IS NULL OR expires_at > now()) "
             f"AND revoked_at IS NULL")
    count = await execute_query(query=query, for_value=True)
    if count is None or not isinstance(count, list):
        bot_logger.error(f"Not able to fetch warnings for user_id {user_id}")
        return None
    return dict(count[0])["count"]


async def revoke_last_action(table: str, user_id: int):
    query = (f"SELECT * FROM {table} "
             f"WHERE user_id = $1 "
             f"AND (expires_at IS NULL OR expires_at > now()) "
             f"AND revoked_at IS NULL "
             f"ORDER BY issued_at DESC LIMIT 1")
    res = await execute_query(query, for_value=True, params=[user_id])

    if isinstance(res, list) and len(res) == 0:
        return False  # la query non ha tornato entry

    if not isinstance(res, list):
        return res

    query = f"UPDATE {table} SET revoked_at = now() WHERE id = $1"

    res = await execute_query(query, for_value=False, params=[dict(res[0])['id']])

    return res


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
        return await get_file(file[-1])


async def get_thread_id(update: Update):
    t_id = update.effective_message.message_thread_id
    if t_id is not None and t_id < 20:
        return t_id
    return None


async def safe_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, message=None):
    if message is not None:
        if not isinstance(message, telegram.Message):
            bot_logger.error("Message is not a telegram.Message object.")
            return
        try:
            await message.delete()
        except telegram.error.BadRequest:
            pass
    else:
        try:
            await update.effective_message.delete()
        except telegram.error.BadRequest:
            pass
