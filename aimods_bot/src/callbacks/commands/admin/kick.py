from typing import Optional, Union

from pyrogram.types import ChatMember as PyroChatMember
from telegram import Update, ChatMemberMember as PTBChatMember

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants import constants as constants
from aimods_bot.src.helpers.database import add_to_table
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.utils.command_parser import parse_command
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, format_user_mention, is_user_id

log = logger.getChild("kick")


ERROR_MESSAGES = constants.ERROR_MESSAGES | {
    "kick_error": "⚠️ Warning\n\n▪️ Errore durante il kick dell'utente (loggato). Riprova."
}


async def kick_user(update: Update, context: CustomContext, full_command: str, delete_flag=False):
    message = update.effective_message

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    parsed = await parse_command(update, context, "kick", full_command)
    if not parsed:
        await send_private_alert(
            update=update,
            context=context,
            text="⚠️ Sintassi del comando non corretta."
        )
        # Potremmo in qualche modo linkare un manuale di utilizzo
        return

    member = parsed["member"]
    if not member["id"]:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["username_404"].format(parsed["user"]),
        )
        return

    uid = member.get("id")
    username = member.get("username")

    if not uid and not username:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["no_user_provided"]
        )
        return

    error_text = _validate_user_status(member["chat_member_instance"])
    if error_text:
        await send_private_alert(
            update=update,
            context=context,
            text=error_text
        )
        return

    user = member["user_instance"]

    kick_result = await _attempt_kick_user(context, user, message.from_user.id)
    if kick_result["status"] == "error":
        await send_private_alert(
            update=update,
            context=context,
            text=kick_result["message"]
        )
        return

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    await _save_kick_to_database(update.effective_user.id, user.id, parsed.get("message", ""))

    confirmation_text = _build_confirmation_message(member, parsed["message"])
    await send_temporary_message(
        update=update,
        context=context,
        text=confirmation_text,
        recipient_id=None,
        delay_delete=300
    )


def _validate_user_status(member: Union[PyroChatMember, PTBChatMember]) -> Optional[str]:
    """Valida lo status dell'utente e restituisce un messaggio di errore se necessario."""

    if not member:
        return ERROR_MESSAGES["cannot_parse_user"]

    if member.status == "left":
        return ERROR_MESSAGES["user_not_in_group"]

    if member.status == "banned" or member.status == "kicked":
        return ERROR_MESSAGES["user_banned"]

    return None


async def _attempt_kick_user_legacy(context: CustomContext, uid: int | str) -> dict:
    try:
        await constants.pyro_instance.unban_chat_member(
            chat_id=context.pydb.group_chat_id,
            user_id=uid
        )
        log.debug(f"Utente {uid} kickato con successo.")
        return {"status": "success", "message": ""}
    except Exception as e:
        if is_user_id(uid):
            try:
                await context.bot.unban_chat_member(
                    chat_id=context.pydb.group_chat_id,
                    user_id=uid
                )
            except Exception as e:
                log.error(f"Errore durante il kick dell'utente {uid}: {e}")
                return {"status": "error", "message": ERROR_MESSAGES["kick_error"]}
        log.error(f"Errore durante il kick dell'utente {uid}: {e}")
        return {"status": "error", "message": ERROR_MESSAGES["kick_error"]}


async def _attempt_kick_user(
        context: CustomContext,
        member: PyroChatMember | PTBChatMember,
        admin_id: int
) -> dict:
    """Tenta il kick dell'utente uid."""

    chat_id = context.pydb.group_chat_id
    user_id = member.user.id  # ID c'è per forza
    username = member.user.username  # Lo username no

    kick_methods = [
        ("ptb", lambda: _kick_with_ptb(context=context, chat_id=chat_id, uid=user_id)),
        ("pyrogram", lambda: _kick_with_pyrogram(chat_id=chat_id, uid=username) if username else None),
        ("pyrogram", lambda: _kick_with_pyrogram(chat_id=chat_id, uid=user_id))
    ]

    for method_name, method_func in kick_methods:
        try:
            method_result = method_func()
            if method_result is None:
                continue  # Metodo non applicabile (es. username con telegram bot)

            await method_result
            log.info(f"Utente {user_id} kickato con successo da {admin_id} ({method_name})")
            return {"status": "success", "message": ""}

        except Exception as e:
            log.warning(f"Fallimento {method_name} per kick utente {user_id}: {e}")
            continue

    # Tutti i metodi falliti
    log.error(f"Tutti i metodi di kick falliti per utente {user_id}")
    return {"status": "error", "message": ERROR_MESSAGES["kick_error"]}


async def _kick_with_pyrogram(chat_id: int, uid: Union[str, int]):
    """Helper per kick con pyrogram (ban + unban)"""
    await constants.pyro_instance.ban_chat_member(chat_id=chat_id, user_id=uid)
    await constants.pyro_instance.unban_chat_member(chat_id=chat_id, user_id=uid)


async def _kick_with_ptb(context: CustomContext, chat_id: int, uid: int):
    """Helper per kick con PTB (unban = kick)"""
    await context.bot.unban_chat_member(chat_id=chat_id, user_id=uid)


async def _save_kick_to_database(admin_id: int, user_id: int, reason: str):
    """Salva i dati del kick nel database."""
    try:
        await add_to_table("kicks", {
            "admin": admin_id,
            "user_id": user_id,
            "reason": reason
        })
    except Exception as e:
        log.error(f"Errore durante il salvataggio del kick nel database: {e}")


def _build_confirmation_message(member, reason=None):
    """Costruisce il messaggio di conferma del kick."""

    user_mention = format_user_mention(
        member["id"],
        member["username"],
        member["first_name"]
    )

    text = f"🥊 Utente {user_mention} <b>kickato</b>."

    if reason:
        text += f"\n\n<b>Motivo</b>: {reason}."

    text += "\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."
    return text
