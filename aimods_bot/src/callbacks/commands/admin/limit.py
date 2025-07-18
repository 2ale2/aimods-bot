from typing import Union, Optional, Dict
from datetime import datetime

from telegram.error import TelegramError
from telegram.ext import ContextTypes
from pyrogram.types import ChatMember as PyroChatMember, ChatPermissions as PyroChatPermissions
from telegram import Update, ChatMember as PTBChatMember, ChatPermissions as PTBChatPermissions

from aimods_bot.src.helpers.constants import constants
from aimods_bot.src.helpers.constants.permissions import permissions_texts, Permissions as Permissions, \
    get_ptb_permissions, get_pyro_permissions
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.utils.command_parser import parse_command
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, format_user_mention, add_fucking_at
from aimods_bot.src.helpers.utils.time_utils import format_time_as_rome, get_until_date
from aimods_bot.src.helpers.utils.user_utils import get_member_permissions
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("limit")


ERROR_MESSAGES = constants.ERROR_MESSAGES | {
    "limit_error": "⚠️ Warning\n\n▪️ Errore durante la limitazione dell'utente (loggato). Riprova."
}


async def limit_user(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str, delete_flag=False):
    message = update.effective_message

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    parsed = await parse_command(update, context, "limit", full_command)
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
    until_date = parsed["duration"]
    reason = parsed["message"]
    permissions = parsed["permissions"]

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

    old_permissions = await get_member_permissions(
        context=context,
        chat_member=member.get("chat_member_instance")
    )
    
    response = await _attempt_limit_user(
        context=context,
        member=member,
        permissions=permissions,
        until=until_date,
        admin_id=message.from_user.id
    )
    if response["status"] == "error":
        await send_private_alert(
            update=update,
            context=context,
            text=reason
        )
        return

    confirmation_text = _build_confirmation_text(
        member=member,
        old_permissions=old_permissions,
        new_permissions=response["permissions"],
        until_date=until_date,
        reason=reason
    )

    await send_temporary_message(
        update=update,
        context=context,
        text=confirmation_text,
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


async def _attempt_limit_user(
        context: ContextTypes.DEFAULT_TYPE,
        member: dict,
        permissions: list[int],
        until: datetime,
        admin_id: int
) -> dict:
    chat_member = member.get("chat_member_instance")
    user_id = member.get("id")
    username = member.get("username")
    until = get_until_date(until)

    new_permissions = await _parse_permissions(
        context=context,
        permissions=permissions,
        chat_member=chat_member
    )

    limit_methods = [
        ("pyro_username", (lambda: _limit_with_pyro(
            context=context,
            user_id=username,
            permissions=new_permissions["pyro_permissions"],
            until_date=until) if username else None)
        ),
        ("pyro_id", lambda: _limit_with_pyro(
            context=context,
            user_id=user_id,
            permissions=new_permissions["pyro_permissions"],
            until_date=until)
        ),
        ("ptb", lambda: _limit_with_ptb(
            context=context,
            user_id=user_id,
            permissions=new_permissions["pyro_permissions"],
            until_date=until)
        )
    ]

    for method_name, method_func in limit_methods:
        if method_func is None:
            continue  # Metodo non applicabile (es. username con telegram bot)

        response = await method_func()
        if not response:
            continue

        log.info(f"Utente {user_id} limitato con successo da {admin_id} ({method_name})")
        return _create_success_response(permissions=new_permissions["pyro_permissions"])

    log.error(f"Tutti i metodi di limitazione falliti per utente {user_id}")
    return _create_error_response(
        permissions=new_permissions["pyro_permissions"],
        error_message=ERROR_MESSAGES["limit_error"]
    )


async def _parse_permissions(
        context: ContextTypes.DEFAULT_TYPE,
        permissions: list[int],
        chat_member: Union[PyroChatMember, PTBChatMember],
        unlimit=False
) -> Optional[Dict[str, Union[PTBChatPermissions, PyroChatPermissions]]]:
    """Trasforma la list di interi in lista di permessi. Tiene conto dei permessi attuali."""

    enum_permissions = Permissions

    actual_permissions = await get_member_permissions(
        context=context,
        chat_member=chat_member
    )
    if permissions == [11]:
        return {
            "ptb_permissions": get_ptb_permissions(not unlimit),
            "pyro_permissions": get_pyro_permissions(not unlimit)
        }
    # La struttura di PTBChatPermissions e PyroChatPermission è praticamente identica: PyroChatPermissions ha
    # l'attributo 'can_send_media_messages' in più, che è un helper.
    d = {p.name: (actual_permissions[p.name] if p.value not in permissions else unlimit) for p in enum_permissions}

    return {
        "ptb_permissions": PTBChatPermissions(**d),
        "pyro_permissions": PyroChatPermissions(**d)
    }


async def _limit_with_ptb(
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        permissions: PTBChatPermissions,
        until_date: datetime,
        use_independent_chat_permissions=True
) -> bool:
    try:
        await context.bot.restrict_chat_member(
            chat_id=int(context.bot_data["group_chat_id"]),
            user_id=user_id,
            until_date=until_date,
            permissions=permissions,
            use_independent_chat_permissions=use_independent_chat_permissions
        )
        log.info(f"Utente {user_id} limitato: {permissions}")
        return True
    except TelegramError as e:
        log.error(f"Non è stato possibile limitare l'utente {user_id} (metodo: PTB): {e}")
        return False


async def _limit_with_pyro(
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int | str,
        permissions: PyroChatPermissions,
        until_date: datetime,
        use_independent_chat_permissions=True
) -> bool:
    try:
        await constants.pyro_instance.restrict_chat_member(
            chat_id=int(context.bot_data["group_chat_id"]),
            user_id=add_fucking_at(user_id) if isinstance(user_id, str) else user_id,
            until_date=until_date,
            permissions=permissions,
            use_independent_chat_permissions=use_independent_chat_permissions
        )
        log.info(f"Utente {user_id} limitato: {permissions}")
        return True
    except Exception as e:
        log.error(f"Non è stato possibile limitare l'utente {user_id} (metodo: Pyro): {e}")
        return False


def _create_error_response(permissions: Union[PTBChatPermissions, PyroChatPermissions], error_message: str) -> dict:
    return {
        "status": "error",
        "permissions": permissions,
        "message": error_message
    }


def _create_success_response(permissions: Union[PTBChatPermissions, PyroChatPermissions]) -> dict:
    return {
        "status": "success",
        "permissions": permissions,
        "message": ""
    }


def _build_confirmation_text(
        member: dict,
        old_permissions: Union[PTBChatPermissions, PyroChatPermissions],
        new_permissions: Union[PTBChatPermissions, PyroChatPermissions],
        until_date: Optional[datetime],
        reason: Optional[str],
        unlimit=False
) -> str:
    user_id = member.get("id")
    username = member.get("username")
    first_name = member.get("first_name")
    mention = format_user_mention(user_id=user_id, username=username, first_name=first_name)
    old_permissions = old_permissions.to_dict()
    new_permissions = new_permissions.to_dict()

    permission_text = ""
    sign = "➖" if unlimit else "➕"

    for el in old_permissions:
        if old_permissions[el] != new_permissions[el]:
            permission_text += f"    {sign} <i>{permissions_texts[el]}</i>\n"

    if not unlimit:
        confirmation_text = f"🔒 Utente {mention} <b>limitato</b> "

        if until_date:
            confirmation_text += f"{format_time_as_rome(until_date)}"

        confirmation_text += "❓ <u>Permessi Rimossi</u>\n\n"
    else:
        confirmation_text = (f"🔓 Utente {mention} <b>non più limitato</b>.\n\n"
                             f"❓ <u>Permessi Aggiunti</u>\n\n")

    confirmation_text += f"{permission_text}\n"

    if reason:
        confirmation_text += f"<b>Motivo<b>: {reason}\n"

    confirmation_text += "\nℹ Questo messaggio verrà rimosso in 5 minuti."

    return confirmation_text
