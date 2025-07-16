import pytz
from telegram import Update
from telegram.ext import ContextTypes
from pyrogram.errors import PeerIdInvalid
from datetime import datetime

import aimods_bot.src.helpers.constants.constants as constants
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, resolve_chat_member, normalize_user, is_username, format_user_mention
from aimods_bot.src.helpers.utils.user_utils import user_is_banned
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.command_parser import parse_command
from aimods_bot.src.helpers.utils.time_utils import zero_datetime, get_until_date, format_time_as_rome
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.database import add_to_table, revoke_last_action

log = logger.getChild("ban_command")


ERROR_MESSAGES = {
    "no_user": "⚠️ Warning\n\n▪️ Se non rispondi ad un messaggio, devi indicare un utente.",
    "user_already_unbanned": "⚠️ Warning\n\n▪️ L'utente è già sbannato.",
    "user_already_banned": "⚠️ Warning\n\n▪️ L'utente è già bannato.",
    "ban_error": "❌ Errore in fase di ban dell'utente (loggato).",
    "db_log_error": ("⚠️ Warning\n\n▪️ L'utente è stato bannato con successo, ma non è stato possibile "
                     "loggare nel database. Contatta subito l'amministratore di sistema per risolvere il problema."),
    "no_ban_found": "⚠️ Nessun ban attivo trovato per questo utente.",
    "db_error": "❌ Errore durante la revoca del ban nel DB (loggato).",
    "unban_error": "❌ Errore in fase di unban dell'utente (loggato)."
}

# ====== BAN ======

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str, delete_flag=False):
    message = update.effective_message

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    parsed = await parse_command(update, context, "ban", full_command)
    if not parsed:
        return

    member = parsed["member"]
    uid = member.get("username") or member.get("id")

    if uid is None:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["no_user"]
        )
        return

    reason = parsed["message"]
    until = get_until_date(parsed["duration"])

    ban_result = await _attempt_ban_user(context, uid, until, member, reason, update.effective_user.id)

    if ban_result["status"] == "blacklisted":
        await send_temporary_message(
            update,
            context,
            text=ban_result["message"],
            delay_delete=300
        )
        return
    elif ban_result["status"] == "error":
        await send_private_alert(update, context, ban_result["message"])
        return

    if parsed["username_not_participant"]:
        member = await _resolve_member_for_logging(context, member, update)
        if member is None:
            confirmation_text = _build_confirmation_message(uid, until, reason)
            await send_temporary_message(update, context, confirmation_text, delay_delete=300)
            await send_private_alert(update, context, ERROR_MESSAGES["db_log_error"])
            return

    await _log_ban_to_database(member, update.effective_user.id, reason, until)

    confirmation_text = _build_confirmation_message(member, until, reason)
    await send_temporary_message(update, context, confirmation_text, delay_delete=300)


async def _attempt_ban_user(
        context: ContextTypes.DEFAULT_TYPE,
        uid: int | str,
        until: datetime,
        member: dict,
        reason: str,
        admin_id: int
):
    """
    Tenta di bannare un utente, con fallback a blacklist.

    Returns:
        dict: {"status": "success"|"blacklisted"|"error", "message": str}
    """
    if await user_is_banned(context, uid):
        return {"status": "error", "message": ERROR_MESSAGES["user_already_banned"]}

    try:
        await constants.pyro_instance.ban_chat_member(
            chat_id=context.bot_data["group_chat_id"],
            user_id=uid,
            until_date=until
        )
        log.info(f"Utente {uid} bannato con successo da {admin_id}")
        return {"status": "success", "message": ""}

    except PeerIdInvalid:
        log.warning(f"PeerIdInvalid per utente {uid}, aggiunta a blacklist")
        return await _add_to_blacklist(context, member, until, reason, admin_id)

    except Exception as e:
        log.exception(f"Errore in fase di ban dell'utente {uid}: {e}")
        return {"status": "error", "message": ERROR_MESSAGES["ban_error"]}


async def _add_to_blacklist(context, member, until, reason, admin_id):
    """
    Aggiunge un utente alla blacklist come fallback.
    """
    context.bot_data.setdefault("ban_list", {})
    context.bot_data["ban_list"][member["id"]] = {
        "expires_at": until.astimezone(pytz.UTC) if until != zero_datetime() else None,
        "reason": reason or None,
        "admin": admin_id
    }

    blacklist_message = (
        f"🖊 Utente {format_user_mention(member['id'], member['username'], member['first_name'])} "
        f"<b>aggiunto in blacklist</b>. Verrà bannato al primo ingresso.\n\n"
        f"ℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."
    )

    return {"status": "blacklisted", "message": blacklist_message}


async def _resolve_member_for_logging(context, member, update):
    """
    Risolve un membro per il logging nel database.

    Returns:
        dict|None: Dati del membro risolto o None se errore
    """
    try:
        resolving_attempt = await resolve_chat_member(
            context=context,
            user_identifier=member["username"]
        )
        if resolving_attempt["status"] == "success":
            return normalize_user(resolving_attempt["member"])

        # Username non trovato anche se il ban è andato a buon fine
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["db_log_error"]
        )
        return None
    except Exception as e:
        log.error(f"Errore durante la risoluzione del membro {member['username']}: {e}")
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["db_log_error"]
        )
        return None


async def _log_ban_to_database(member, admin_id, reason, until):
    """
    Logga il ban nel database.
    """
    if not member.get("id"):
        log.warning("Impossibile loggare ban: membro senza ID")
        return

    try:
        await add_to_table("bans", {
            "admin": admin_id,
            "user_id": int(member["id"]),
            "reason": reason or "",
            "expires_at": until if until != zero_datetime() else None
        })
        log.info(f"Ban dell'utente {member['id']} loggato nel database")
    except Exception as e:
        log.error(f"Errore durante il logging del ban nel database: {e}")


# ====== UNBAN ======


async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str, delete_flag=False):
    message = update.effective_message

    parsed = await parse_command(update, context, "ban", full_command)
    if not parsed:
        return

    member = parsed["member"]
    uid = member["username"] or member["id"]

    if not uid:
        return await send_private_alert(update, context, "⚠️ Devi indicare l'utente da sbannare.")

    blacklist_removed = _remove_from_blacklist(context, member["id"])

    if blacklist_removed:
        log.info(f"Utente {uid} rimosso dalla blacklist da {update.effective_user.id}")
        unban_type = "blacklist"
    else:
        unban_result = await _attempt_unban_user(context, member, uid, update.effective_user.id)
        if unban_result["status"] == "error":
            await send_private_alert(update, context, unban_result["message"])
            return
        unban_type = "ban"

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    reason = parsed["message"]
    confirmation_text = _build_confirmation_message(member, unban_type, reason, popped=blacklist_removed, unban=True)
    await send_temporary_message(update, context, confirmation_text, delay_delete=300)


def _remove_from_blacklist(context, user_id):
    """Rimuove un utente dalla blacklist se presente."""

    ban_list = context.bot_data.get("ban_list", {})
    removed_entry = ban_list.pop(user_id, None)

    if removed_entry:
        log.info(f"Utente {user_id} rimosso dalla blacklist")
        return True

    return False


async def _attempt_unban_user(context, member, uid, admin_id):
    """
    Tenta di sbannare un utente revocando il ban dal database e dal gruppo.

    Returns:
        dict: {"status": "success"|"error", "message": str}
    """
    if not await user_is_banned(context, uid):
        return {"status": "error", "message": ERROR_MESSAGES["user_already_unbanned"]}

    try:
        await constants.pyro_instance.unban_chat_member(
            chat_id=context.bot_data["group_chat_id"],
            user_id=uid
        )
        log.info(f"Utente {uid} sbannato con successo da {admin_id}")
    except Exception as e:
        log.exception(f"Errore in fase di unban dell'utente {uid}: {e}")
        return {"status": "error", "message": ERROR_MESSAGES["unban_error"]}

    db_result = await revoke_last_action("bans", int(member["id"]))

    if db_result is False:
        return {"status": "success", "database_error": ERROR_MESSAGES["no_ban_found"]}
    elif not db_result:
        log.error(f"Errore database durante revoca ban per utente {member['id']}")
        return {"status": "success", "database_error": ERROR_MESSAGES["db_error"]}

    return {"status": "success", "database_error": None}


# ====== UTILITIES ======

def _build_confirmation_message(member, until, reason=None, unban=False, popped=None):
    """Costruisce il messaggio di conferma del ban."""

    if isinstance(member, dict):
        user_mention = format_user_mention(
            member["id"],
            member["username"],
            member["first_name"]
        )
    else:
        if is_username(member):
            user_mention = format_user_mention(user_id=None, username=member, first_name=None)
        else:
            user_mention = format_user_mention(user_id=member, username=None, first_name=None)

    if not unban:
        text = (
            f"🚫 Utente {user_mention} <b>bannato</b> "
            f"{format_time_as_rome(until)}"
        )
    else:
        text = (f"⛓️‍💥 Utente {user_mention} <b>bannato</b> "
                f"<b>{'sbannato' if not popped else 'rimosso dalla blacklist'}</b>.")

    if reason:
        text += f"\n\n<b>Motivo</b>: {reason}."

    text += "\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."
    return text
