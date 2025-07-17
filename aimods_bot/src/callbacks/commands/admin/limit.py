from typing import Union
from telegram.ext import ContextTypes
from pyrogram.types import ChatMember as PyroChatMember, User as PyroUser
from telegram import Update, ChatMember as PTBChatMember, User as PTBUser

from aimods_bot.src.helpers.constants.constants import ERROR_MESSAGES
from aimods_bot.src.helpers.constants.permissions import permissions_texts, Permissions as Permissions
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.utils.command_parser import parse_command
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete


async def limit_user(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str, delete_flag=False):
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




async def _validate_user_status(member: Union[PyroChatMember, PTBChatMember]):
    """Valida lo status dell'utente e restituisce un messaggio di errore se necessario."""

    if not member:
        return ERROR_MESSAGES["cannot_parse_user"]

    if member.status == "left":
        return ERROR_MESSAGES["user_not_in_group"]

    if member.status == "banned" or member.status == "kicked":
        return ERROR_MESSAGES["user_banned"]

    return None


async def _attempt_limit_user(
        context: ContextTypes.DEFAULT_TYPE,
        member: dict,
        permissions: list[int],
        admin_id: int
) -> dict:
    permissions, new_permissions = Permissions, {}

    # Necessario distinguere tra le due classi PTBChatMember e PyroChatMember
