import pytz
from telegram import Update
from telegram.ext import ContextTypes
from pyrogram.errors import PeerIdInvalid

import aimods_bot.src.helpers.constants.constants as constants
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, resolve_chat_member
from . import get_until_date, format_time_as_rome, format_user_mention
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.command_parser import parse_command
from aimods_bot.src.helpers.utils.time_utils import zero_datetime
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.database import add_to_table, revoke_last_action

log = logger.getChild("ban_command")


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str, delete_flag=False):
    message = update.effective_message

    parsed = await parse_command(update, context, "ban", full_command)
    if not parsed:
        return

    member = parsed["member"]
    uid = member.get("username") or member.get("id")

    if uid is None:
        await send_private_alert(
            update=update,
            context=context,
            text="⚠️ Warning\n\n▪️ Se non rispondi ad un messaggio, devi indicare un utente."
        )
        return

    reason = parsed["message"]
    until = get_until_date(parsed["duration"])

    try:
        await constants.pyro_instance.ban_chat_member(
            chat_id=context.bot_data["group_chat_id"],
            user_id=uid,
            until_date=until
        )
    except PeerIdInvalid:
        # fallback: aggiunta alla blacklist
        context.bot_data.setdefault("ban_list", {})
        context.bot_data["ban_list"][member["id"]] = {
            "expires_at": until.astimezone(pytz.UTC) if until != zero_datetime() else None,
            "reason": reason or None,
            "admin": update.effective_user.id
        }

        await send_temporary_message(
            update,
            context,
            text=(f"🖊 Utente {format_user_mention(member["id"], member["username"], member["first_name"])} "
                  f"<b>aggiunto in blacklist</b>. Verrà bannato al primo ingresso.\n\n"
                  f"ℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."),
            delay_delete=300
        )
        return
    except Exception as e:
        log.exception(f"Errore in fase di ban dell'utente: {e}")
        await send_private_alert(update, context, "❌ Errore in fase di ban dell'utente (loggato).")
        return

    if parsed["username_not_participant"]:
        resolving_attempt = await resolve_chat_member(context=context, user_identifier=member["username"])
        if resolving_attempt:
            member = _normalize_user(resolving_attempt.user)
        else:
            # Per qualche motivo lo username non è stato trovato anche se il ban è andato a buon fine.
            # È necessario in questo caso aggiungere il log al DB manualmente.
            await send_private_alert(
                update=update,
                context=context,
                text="⚠️ Warning\n\n▪️ L'utente è stato bannato con successo, ma non è stato possibile "
                     "loggare nel database. Contatta subito l'amministratore di sistema per risolvere il problema."
            )

    if member["id"]:
        await add_to_table("bans", {
            "admin": update.effective_user.id,
            "user_id": int(member["id"]),
            "reason": reason or "",
            "expires_at": until if until != zero_datetime() else None
        })

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    text = (
        f"🚫 Utente {format_user_mention(member["id"], member["username"], member["first_name"])} <b>bannato</b> "
        f"{format_time_as_rome(until)}"
    )
    if reason:
        text += f"\n<b>Motivo</b>: {reason}."

    text += "\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."
    await send_temporary_message(update, context, text, delay_delete=300)


async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str, delete_flag=False):
    message = update.effective_message

    parsed = await parse_command(update, context, "ban", full_command)
    if not parsed:
        return

    member = parsed["member"]
    uid = member["username"] or member["id"]

    if not uid:
        return await send_private_alert(update, context, "⚠️ Devi indicare l'utente da sbannare.")

    if not (popped := context.bot_data.get("ban_list", {}).pop(member["id"], None)):
        res = await revoke_last_action("bans", int(member["id"]))
        if res is False:
            return await send_private_alert(update, context, "⚠️ Nessun ban attivo trovato per questo utente.")
        elif not res:
            return await send_private_alert(update, context, "❌ Errore durante la revoca del ban nel DB (loggato).")

        try:
            await constants.pyro_instance.unban_chat_member(
                chat_id=context.bot_data["group_chat_id"],
                user_id=uid
            )
        except Exception as e:
            log.exception(f"Errore in fase di unban dell'utente: {e}")
            return await send_private_alert(update, context, "❌ Errore in fase di unban dell'utente (loggato).")

        if delete_flag and message.reply_to_message:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=message.reply_to_message.message_id
            )

    reason = parsed["message"]

    text = (f"⛓️‍💥 Utente {format_user_mention(member["id"], member["username"], member["first_name"])} "
            f"<b>{'sbannato' if not popped else 'rimosso dalla blacklist'}</b>.")
    if reason:
        text += f"\n<b>Motivo</b>: {reason}."

    text += "\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."
    await send_temporary_message(update, context, text, delay_delete=300)


def _normalize_user(user) -> dict:
    return {
        "id": user.id,
        "username": getattr(user, "username", None),
        "first_name": getattr(user, "first_name", ""),
        "source": user.__class__.__name__
    }
