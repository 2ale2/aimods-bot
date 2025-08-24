import os
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.utils.telegram_utils import format_user_mention, resolve_chat_member, normalize_user
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.time_utils import zero_datetime, format_time_as_rome

log = logger.getChild("bot_logger")

CHANNEL_LOGGER_ID = int(os.getenv("CHANNEL_LOGGER_ID"))


async def log_ban(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        admin_id: int,
        user_id: int,
        until: datetime,
        reason: str = None):
    log.info(f"→ User {user_id} banned by admin {admin_id}. "
             f"{f'Reason: {reason}' if reason else 'No reason specified.'}")
    text = _log_ban_text(
        update=update,
        context=context,
        admin_id=admin_id,
        user_id=user_id,
        until=until,
        reason=reason)

    await context.bot.send_message(
        chat_id=CHANNEL_LOGGER_ID,
        text=text,
        parse_mode=ParseMode.HTML
    )


async def _log_ban_text(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        admin_id: int,
        user_id: int,
        until: datetime = zero_datetime(),
        reason: str = None):
    if user_id == update.effective_user.id:
        user = update.effective_user
        mention = format_user_mention(user_id=user_id, username=user.username, first_name=user.first_name)
    else:
        response = await resolve_chat_member(context=context, user_identifier=user_id)

        if response.get("status", False) == "success":
            member = normalize_user(response["member"])
            mention = format_user_mention(
                user_id=member["id"],
                username=member["username"],
                first_name=member["first_name"]
            )
        else:
            mention = format_user_mention(user_id=user_id)

    response = await resolve_chat_member(context=context, user_identifier=admin_id)
    admin = response["member"]
    admin_mention = format_user_mention(
        user_id=admin_id,
        username=admin.get("username", None),
        first_name=admin.get("first_name", None)
    )

    duration_text = format_time_as_rome(until)
    if duration_text:
        duration_text = "fino al " + duration_text
    else:
        duration_text = "a <b>tempo indeterminato</b>"

    text = ("⛔ #BAN"
            f"👤 <b>Utente</b> – {mention}\n"
            f"🫳 <b>Admin</b> – {admin_mention}\n"
            f"⏳ <b>Scadenza</b> – {duration_text}\n"
            f"❓ <b>Motivo</b> – {reason or '<code>no reason specified</code>'}")

    return text


async def log_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.info(f"→ User {update.effective_user.id} joined.")
    text = _log_join_text(update)

    await context.bot.send_message(
        chat_id=CHANNEL_LOGGER_ID,
        text=text,
        parse_mode=ParseMode.HTML
    )


def _log_join_text(update: Update):
    joined_id = update.effective_user.id
    joined_username = update.effective_user.username
    joined_first_name = update.effective_user.first_name

    mention = format_user_mention(user_id=joined_id, username=joined_username, first_name=joined_first_name)

    text = ("➕ #JOIN\n"
            f"👤 <b>Utente</b> – {mention}\n"
            f"#id{joined_id}")

    return text
