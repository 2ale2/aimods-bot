from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.job_queue import get_valid_thread_id, send_action_message_after
from aimods_bot.src.helpers.models.typed_callback_data import AlertCallbackData, parse_callback_data
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete

"""
NOTA - Questo modulo al momento tratta gli alert che vengono mandati dal bot all'utente che esegue
un'azione qualora ci sia qualcosa che non va (per esempio la sintassi del comando). Tuttavia, l'idea
è far gestire anche gli alert dei messaggi privati scambiati nel gruppo (similmente a come accade per
WhisperBot.
"""


async def send_private_alert(update: Update,
                             context: CustomContext,
                             text: str,
                             user: User | None = None,
                             button_text: str ="Open It Privately 💬",
                             delay: int = 2):
    """Invia un messaggio privato in una chat pubblica apribile solo dal destinatario."""

    user = user or update.effective_user

    alert_id = str(uuid4())
    context.pydu.persistent.alerts[alert_id] = text

    callback_data = AlertCallbackData(
        user_id=user.id,
        alert_id=alert_id,
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(button_text, callback_data=str(callback_data))
    ]])

    message_text = f"🔐 Messaggio per {user.mention_html()}"
    thread_id = get_valid_thread_id(update)

    if delay > 0:
        await send_action_message_after(
            update=update,
            context=context,
            text=message_text,
            time=delay,
            thread_id=thread_id,
            reply_markup=keyboard
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=thread_id,
            text=message_text,
            reply_markup=keyboard
        )


async def open_private_alert(update: Update, context: CustomContext):
    """Mostra il contenuto salvato di un alert privato all'utente che ha premuto il pulsante inline."""
    query = update.callback_query

    # noinspection PyTypeChecker
    parsed = parse_callback_data(query.data)

    if not isinstance(parsed, AlertCallbackData):
        raise ValueError(f"Typed callback query not valid: expected AlertCallbackData, got {type(parsed).__name__}")

    if parsed.user_id != update.effective_user.id:
        return

    alerts = context.pydu.persistent.alerts
    text = alerts.pop(parsed.alert_id, None)

    if text is None:
        await query.answer(text="⚠️ Messaggio già visto o non più valido.", show_alert=True)
    else:
        await query.answer(text=text, show_alert=True)

    await safe_delete(update, context)
