from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.callbacks.commands.admin import format_user_mention
from aimods_bot.src.helpers.database import add_to_table
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.utils.command_parser import parse_command
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import resolve_chat_member, safe_delete

log = logger.getChild("kick")


ERROR_MESSAGES = {
    "no_user": "⚠️ Warning\n\n▪️ Se non rispondi ad un messaggio, devi indicare un utente.",
    "user_not_found": "⚠️ Warning\n\n▪️ Non riesco a risolvere l'utente specificato, riprova.",
    "user_not_in_group": "⚠️ Warning\n\n▪️ L'utente non è nel gruppo.",
    "user_already_banned": "⚠️ Warning\n\n▪️ L'utente è bannato."
}


async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str, delete_flag=False):
    message = update.effective_message

    parsed = await parse_command(update, context, "kick", full_command)
    if not parsed:
        return

    member = parsed["member"]
    uid = member.get("username") or member.get("id")

    if not uid:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["no_user"]
        )
        return

    chat_member = await resolve_chat_member(context, uid)

    error_text = _validate_user_status(chat_member)
    if error_text:
        await send_private_alert(
            update=update,
            context=context,
            text=error_text
        )
        return

    user = chat_member.user

    try:
        await context.bot.unban_chat_member(
            chat_id=context.bot_data["group_chat_id"],
            user_id=uid
        )
        log.debug(f"Utente {uid} kickato con successo.")
    except Exception as e:
        log.error(f"Errore durante il kick dell'utente {uid}: {e}")
        await send_private_alert(
            update=update,
            context=context,
            text="⚠️ Warning\n\n▪️ Errore durante il kick dell'utente (loggato). Riprova."
        )
        return

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    mention = format_user_mention(user.id, user.username, user.first_name)

    confirmation_text = f"🥊 Utente {mention} <b>kickato</b>."

    if parsed["message"]:
        confirmation_text += f"\n<b>Motivo</b>: {parsed['message']}."

    await _save_kick_to_database(update.effective_user.id, user.id, parsed.get("message", ""))

    confirmation_text += "\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."
    await send_temporary_message(update, context, confirmation_text, delay_delete=300)


def _validate_user_status(chat_member) -> str | None:
    """
    Valida lo status dell'utente e restituisce un messaggio di errore se necessario.

    Args:
        chat_member: Il ChatMember da validare

    Returns:
        Messaggio di errore o None se l'utente è valido
    """
    if not chat_member:
        return ERROR_MESSAGES["user_not_found"]

    if chat_member.status == "left":
        return ERROR_MESSAGES["user_not_in_group"]

    if chat_member.status == "banned":
        return ERROR_MESSAGES["user_already_banned"]

    return None


async def _save_kick_to_database(admin_id: int, user_id: int, reason: str):
    """
    Salva i dati del kick nel database.

    Args:
        admin_id: ID dell'admin che ha eseguito il kick
        user_id: ID dell'utente kickato
        reason: Motivo del kick
    """
    try:
        await add_to_table("kicks", {
            "admin": admin_id,
            "user_id": user_id,
            "reason": reason
        })
    except Exception as e:
        log.error(f"Errore durante il salvataggio del kick nel database: {e}")
