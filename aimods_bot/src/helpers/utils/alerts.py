from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.job_queue import get_valid_thread_id, send_action_message_after
from aimods_bot.src.helpers.utils.telegram_utils import validate_callback_structure, safe_delete


async def send_private_alert(update: Update,
                             context: CustomContext,
                             text: str,
                             button_text="Open It Privately 💬",
                             delay=2):
    """
    Invia un messaggio privato in una chat pubblica apribile solo dal destinatario.
    """

    if "alerts" not in context.user_data:
        context.user_data["alerts"] = {}

    alert_id = str(uuid4())
    context.pydu.persistent.alerts[alert_id] = text

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
            thread_id=thread_id,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=thread_id,
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def open_private_alert(update: Update, context: CustomContext):
    """
    Mostra il contenuto salvato di un alert privato all'utente che ha premuto il pulsante inline.
    """

    _, user_id, alert_id = validate_callback_structure(
        callback_data=update.callback_query.data,
        expected_fields=[
            {"type": "literal", "value": "alert"},
            # L'ID deve essere int, ma può anche essere str(ID), mentre non può essere int("@username)"
            # Quindi metto prima int.
            {"type": [int, str]},
            {"type": str}
        ],
        should_be="alert_<user:int|@username>_<alertId:str>"
    )

    if user_id != update.effective_user.id:
        return

    user_alerts = context.user_data.get("alerts", {})
    if alert_id not in user_alerts:
        await update.callback_query.answer(
            text="⚠️ Messaggio già visto o non più valido.",
            show_alert=True
        )
    else:
        await update.callback_query.answer(
            text=context.user_data["alerts"][alert_id],
            show_alert=True
        )

    await safe_delete(update, context)
    return
