from datetime import datetime
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.callbacks.commands.admin.limit import limit_user
from aimods_bot.src.helpers.constants.constants import ERROR_MESSAGES
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.utils.command_parser import parse_command
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, format_user_mention
from aimods_bot.src.helpers.utils.time_utils import timedelta_to_seconds, format_time_as_rome, get_until_date


async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str, delete_flag=False):
    message = update.effective_message

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    parsed = await parse_command(update=update, context=context, command="mute", full_command=full_command)
    if not parsed:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["command_syntax_error"],
        )
        return

    user = parsed["user"]
    reason = parsed["message"]
    duration = parsed["duration"]

    time = str(timedelta_to_seconds(duration)) + " secondi" if duration else ''

    limit_command = f"/limit {user} 0 {time} {reason or ''}".rstrip().replace("  ", " ")

    response = await limit_user(
        update=update,
        context=context,
        full_command=limit_command,
        delete_flag=delete_flag,
        mute_flag=True
    )

    if response:
        confirmation_text = _build_confirmation_message(
            member=parsed["member"],
            until_date=get_until_date(duration),
            reason=reason,
            unmute=False
        )

        await send_temporary_message(
            update=update,
            context=context,
            text=confirmation_text,
            recipient_id=None,
            delay_delete=300
        )


async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str, delete_flag=False):
    message = update.effective_message

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    parsed = await parse_command(update=update, context=context, command="mute", full_command=full_command)
    if not parsed:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["command_syntax_error"],
        )
        return

    limit_command = f"/unlimit {parsed["user"]} 0".replace("  ", " ")

    response = await limit_user(
        update=update,
        context=context,
        full_command=limit_command,
        delete_flag=delete_flag,
        mute_flag=True)

    if response:
        confirmation_text = _build_confirmation_message(
            member=parsed["member"],
            until_date=None,
            reason=None,
            unmute=True
        )

        await send_temporary_message(
            update=update,
            context=context,
            text=confirmation_text,
            recipient_id=None,
            delay_delete=300
        )


def _build_confirmation_message(
        member: dict,
        until_date: Optional[datetime],
        reason: Optional[str],
        unmute=False
) -> str:
    user_id = member.get("id")
    username = member.get("username")
    first_name = member.get("first_name")
    mention = format_user_mention(user_id=user_id, username=username, first_name=first_name)

    sign = "🔏" if not unmute else "🔓"

    confirmation_text = f"{sign} Utente {mention} <b>{'s' if unmute else ''}mutato</b>"

    if not unmute:
        if until_date:
            duration_text = format_time_as_rome(until_date)

            if duration_text:
                duration_text = "fino al " + duration_text
            else:
                duration_text = "a <b>tempo indeterminato</b>"

            confirmation_text += f" {duration_text}."

        if reason:
            confirmation_text += f"\n\n<b>Motivo</b>: {reason}"
    else:
        confirmation_text += "."

    confirmation_text += "\n\nℹ <i>Questo messaggio verrà rimosso in 5 minuti</i>."

    return confirmation_text
