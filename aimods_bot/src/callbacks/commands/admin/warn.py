import pytz
from datetime import datetime
from typing import Union, Optional
from telegram.ext import ContextTypes
from pyrogram.types import ChatMember as PyroChatMember, User as PyroUser
from telegram import Update, ChatMember as PTBChatMember, User as PTBUser

from aimods_bot.src.callbacks.commands.admin.ban import attempt_ban_user
from aimods_bot.src.core.exceptions import MissingParameterException
from aimods_bot.src.helpers.database import add_to_table, revoke_last_action
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.constants import constants as constants
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.utils.command_parser import parse_command
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, format_user_mention
from aimods_bot.src.helpers.utils.time_utils import zero_datetime, get_until_date, format_time_as_rome
from aimods_bot.src.helpers.utils.user_utils import get_user_warnings_count, erase_user_warnings


log = logger.getChild("warn")

ERROR_MESSAGES = constants.ERROR_MESSAGES | {
    "warn_error": "⚠️ Warning\n\n▪️ Errore durante il warn dell'utente (loggato). Riprova.",
    "unable_to_add_warning_to_table": "❌ Error\n\n▪️ Errore durante l'aggiunta del warn al database (loggato).",
    "warn_count_error": "❌ Error\n\n▪️ Errore durante il conteggio dei warn dell'utente {} (loggato).",
    "user_already_banned": "⚠️ Warning\n\n▪️ L'utente è già bannato.",
    "ban_error": "❌ Error\n\n▪️ Errore in fase di ban dell'utente (loggato).",
    "revoke_action_error": "❌ Error\n\n▪️ Non sono riuscito a revocare l'ultimo worn per {} (loggato).",
    "no_warns": "⚠️ Warning\n\n▪️ L'utente non ha ammonizioni attive.",
    "missing_reason": "⚠️ Warning\n\n▪️ Devi indicare una motivazione."
}

MAX_WARNS = 3


async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str, delete_flag=False):
    message = update.effective_message

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    parsed = await parse_command(update, context, "warn", full_command)
    if not parsed:
        return

    member = parsed["member"]
    if not member["id"]:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["username_404"].format(parsed["user"]),
        )
        return

    if not parsed["message"]:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["missing_reason"]
        )
        return

    uid = member.get("id")
    username = member.get("username")

    if not uid and not username:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["no_user"]
        )
        return

    error_text = await _validate_user_status(member["chat_member_instance"])
    if error_text:
        await send_private_alert(
            update=update,
            context=context,
            text=error_text
        )
        return

    until_date = get_until_date(parsed["duration"])
    reason = parsed["message"]
    admin_id = update.effective_user.id

    response = await _attempt_warn_user(
        context=context,
        member=member,
        until_date=until_date,
        reason=reason,
        admin_id=admin_id
    )

    if response["status"] == "error":
        await send_private_alert(
            update=update,
            context=context,
            text=response["message"]
        )
        return

    confirmation_text = _build_confirmation_message(
        user=member["user_instance"],
        until=until_date,
        reason=reason,
        action=response["action"],
        warn_count=response["warn_count"]
    )

    await send_temporary_message(
        update=update,
        context=context,
        text=confirmation_text,
        recipient_id=None,
        delay_delete=300
    )


async def unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str, delete_flag=False):
    message = update.effective_message

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    parsed = await parse_command(update, context, "warn", full_command)
    if not parsed:
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
            text=ERROR_MESSAGES["no_user"]
        )
        return

    error_text = await _validate_user_status(member["chat_member_instance"])
    if error_text:
        await send_private_alert(
            update=update,
            context=context,
            text=error_text
        )
        return

    response = await _attempt_unwarn_user(member=member)
    if response["status"] == "error":
        await send_private_alert(
            update=update,
            context=context,
            text=response["message"]
        )
        return

    confirmation_text = _build_confirmation_message(
        user=member["user_instance"],
        reason=None,
        until=None,
        action=response["action"],
        warn_count=response["warn_count"]
    )

    await send_temporary_message(
        update=update,
        context=context,
        text=confirmation_text,
        recipient_id=None,
        delay_delete=300
    )


async def _validate_user_status(member: Union[PyroChatMember, PTBChatMember]):
    """Valida lo status dell'utente e restituisce un messaggio di errore se necessario."""

    if not member:
        return ERROR_MESSAGES["cannot_parse_user"]

    if member.status == "left":
        return ERROR_MESSAGES["user_not_in_group"]

    if member.status == "banned" or member.status == "kicked":
        return ERROR_MESSAGES["user_banned"]

    return None


async def _attempt_warn_user(
        context: ContextTypes.DEFAULT_TYPE,
        member: dict,
        until_date: datetime,
        reason: str,
        admin_id: int
) -> dict:
    """Tenta di ammonire un utente."""

    user_id = member["user_instance"].id

    response = await add_to_table("warnings", {
        "admin": admin_id,
        "user_id": user_id,
        "expires_at": until_date.astimezone(pytz.UTC) if until_date != zero_datetime() else None,
        "reason": reason
    })
    if not response:
        return _create_error_response(ERROR_MESSAGES["unable_to_add_warning_to_table"])

    count = await get_user_warnings_count(user_id=user_id)
    if count is None:
        return _create_error_response(ERROR_MESSAGES["warn_count_error"].format(user_id))

    if count >= MAX_WARNS:
        response = await attempt_ban_user(
            context=context,
            uid=user_id,
            until=until_date,
            member=member,
            reason=reason,
            admin_id=admin_id
        )
        if response["status"] == "error":
            return _create_error_response(ERROR_MESSAGES[response["message"]])

        errors = await erase_user_warnings(user_id=user_id)
        if errors:
            log.warning(f"Non è stato possibile revocare le ammonizioni {', '.join(errors)} per l'utente {user_id}.")

        return _create_success_response(action="banned", warn_count=count)

    return _create_success_response(action="warned", warn_count=count)


async def _attempt_unwarn_user(member: dict) -> dict:
    user_id = member["user_instance"].id

    response = await revoke_last_action(table="warnings", user_id=user_id)
    if response is False:
        return _create_error_response(ERROR_MESSAGES["no_warns"])
    if response is None:
        return _create_error_response(ERROR_MESSAGES["revoke_action_error"])

    count = await get_user_warnings_count(user_id=user_id)

    return _create_success_response(action="unwarn", warn_count=count)


def _create_error_response(error_message: str) -> dict:
    return {
        "status": "error",
        "message": error_message
    }


def _create_success_response(action: str, warn_count: int) -> dict:
    return {
        "status": "success",
        "action": action,
        "warn_count": warn_count
    }


def _build_confirmation_message(
        user: Union[PyroUser, PTBUser],
        until: Optional[datetime],
        reason: Optional[str],
        action: Optional[str],
        warn_count: int
) -> str:

    unwarn = bool(action == "unwarn")

    if not unwarn and not action:
        raise MissingParameterException("Se 'unwarn' è False, 'action' deve essere definito.")

    uid = user.id
    username = user.username
    first_name = user.first_name

    mention = format_user_mention(user_id=uid, username=username, first_name=first_name)

    if not unwarn:
        if action == "warned":
            text = (
                f"⚠️ Utente {mention} <b>ammonito</b> ({warn_count}/{MAX_WARNS}) "
                f"{format_time_as_rome(until)}"
            )
        else:
            text = (
                f"🚫 Utente {mention} ammonito ({warn_count}/{MAX_WARNS} → <b>bannato</b>) "
                f"{format_time_as_rome(until)}"
            )
        if reason:
            text += f"\n\n<b>Motivo</b>: {reason}."
    else:
        text = f"✅ <b>Ammonizione rimossa</b> per {mention} ({warn_count}/{MAX_WARNS})."

    text += "\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."
    return text
