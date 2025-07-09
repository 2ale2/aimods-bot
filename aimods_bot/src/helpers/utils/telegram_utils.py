import telegram
from aimods_bot.src.helpers.loggers import logger
from uuid import uuid4
from typing import Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.job_queue import send_action_message_after

log = logger.getChild("telegram_utils")


def get_valid_thread_id(update: Update) -> Optional[int]:
    thread_id = update.effective_message.message_thread_id
    if thread_id is not None and thread_id < 20:
        return thread_id
    return None


async def safe_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, message: telegram.Message = None):
    """
    Tenta di eliminare un messaggio Telegram in modo sicuro.
    Se viene fornito 'message', tenta di eliminare quello.
    Altrimenti, tenta di eliminare update.effective_message.
    Ignora errori di tipo BadRequest (es. messaggio già eliminato o non trovato).
    """
    message_to_delete = message if message is not None else update.effective_message

    if message_to_delete is None:
        log.warning("Nessun messaggio valido da eliminare è stato fornito o trovato.")
        return

    try:
        await message_to_delete.delete()
    except telegram.error.BadRequest as e:
        log.warning(f"Impossibile eliminare il messaggio (ID: {message_to_delete.message_id if hasattr(message_to_delete, 'message_id') else 'N/A'}): {e}")
    except AttributeError:
        log.error(f"L'oggetto fornito non è un telegram.Message valido e non ha il metodo delete.")
    except Exception as e:
        log.error(f"Errore inatteso durante l'eliminazione del messaggio: {e}", exc_info=True)


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

    message_text = f"🔐 Message for {update.effective_user.name}"
    thread_id = get_valid_thread_id(update)

    if delay > 0:
        await send_action_message_after(
            update=update,
            context=context,
            text=message_text,
            time=delay,
            additional_job_data={
                "thread_id": thread_id,
                "reply_markup": InlineKeyboardMarkup(keyboard)
            }
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=thread_id,
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )