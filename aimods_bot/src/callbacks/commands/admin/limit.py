from typing import Union, Optional, Dict
from datetime import datetime

from telegram.error import TelegramError
from telegram.ext import ContextTypes
from pyrogram.types import ChatMember as PyroChatMember, ChatPermissions as PyroChatPermissions
from telegram import Update, ChatMember as PTBChatMember, ChatPermissions as PTBChatPermissions

from aimods_bot.src.helpers.constants import constants
from aimods_bot.src.helpers.constants.permissions import permissions_texts, Permissions as Permissions, \
    get_ptb_permissions, get_pyro_permissions
from aimods_bot.src.helpers.database import add_to_table
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.utils.command_parser import parse_command
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, format_user_mention, add_fucking_at, \
    permission_instance_to_dict, resolve_chat_member
from aimods_bot.src.helpers.utils.time_utils import format_time_as_rome, get_until_date
from aimods_bot.src.helpers.utils.user_utils import get_member_permissions
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("limit")


ERROR_MESSAGES = constants.ERROR_MESSAGES | {
    "limit_error": "⚠️ Warning\n\n▪️ Errore durante la limitazione dell'utente (loggato). Riprova.",
    "missing_permissions": "⚠️ Warning\n\n▪️ Permessi mancanti o non validi.",
    "no_changes": "⚠️ Warning\n\n▪️ I permessi indicati non producono cambiamenti "
                  "(può essere anche dovuto alle dipendenze tra permessi)."
}


async def limit_user(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        full_command: str,
        delete_flag=False,
        mute_flag=False
) -> bool:
    message = update.effective_message

    if delete_flag and message.reply_to_message:
        await safe_delete(update, context, message.reply_to_message)

    action = full_command.split()[0][1:]
    is_unlimit = action == "unlimit"

    parsed = await parse_command(update=update, context=context, command=action, full_command=full_command)
    if not parsed:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["command_syntax_error"],
        )
        return False

    member = parsed["member"]
    if not member["id"]:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["username_404"].format(parsed["user"]),
        )
        return False

    uid = member.get("id")
    username = member.get("username")
    until_date = parsed["duration"]
    reason = parsed["message"]
    permissions = parsed["permissions"]
    admin_id = message.from_user.id

    if not uid and not username:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["no_user"]
        )
        return False

    if not permissions:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["missing_permissions"]
        )
        return False

    error_text = await _validate_user_status(member["chat_member_instance"])
    if error_text:
        await send_private_alert(
            update=update,
            context=context,
            text=error_text
        )
        return False

    old_permissions = await get_member_permissions(
        context=context,
        chat_member=member.get("chat_member_instance")
    )
    
    response = await _attempt_limit_unlimit_user(
        context=context,
        member=member,
        permissions=permissions,
        until=until_date,
        admin_id=admin_id,
        unlimit=is_unlimit
    )
    if response["status"] == "error":
        await send_private_alert(
            update=update,
            context=context,
            text=response["message"]
        )
        return False

    new_member = await resolve_chat_member(context=context, user_identifier=username or uid)
    new_permissions = await get_member_permissions(context=context, chat_member=new_member.get("member"))

    diffs = _compare_permissions(old_permissions, new_permissions)

    if not diffs:
        await send_private_alert(
            update=update,
            context=context,
            text=ERROR_MESSAGES["no_changes"]
        )
        return False

    await _log_limit_to_database(
        admin_id=admin_id,
        user_id=uid,
        permissions=permissions,
        until=until_date,
        reason=reason,
        unlimit=is_unlimit
    )

    if not mute_flag:
        confirmation_text = _build_confirmation_text(
            member=member,
            old_permissions=old_permissions,
            new_permissions=response["permissions"],
            until_date=get_until_date(until_date),
            reason=reason,
            unlimit=is_unlimit
        )

        await send_temporary_message(
            update=update,
            context=context,
            text=confirmation_text,
            delay_delete=300
        )

    return True


async def _validate_user_status(member: Union[PyroChatMember, PTBChatMember]):
    """Valida lo status dell'utente e restituisce un messaggio di errore se necessario."""

    if not member:
        return ERROR_MESSAGES["cannot_parse_user"]

    if member.status == "left":
        return ERROR_MESSAGES["user_not_in_group"]

    if member.status == "banned" or member.status == "kicked":
        return ERROR_MESSAGES["user_banned"]

    return None


async def _attempt_limit_unlimit_user(
        context: ContextTypes.DEFAULT_TYPE,
        member: dict,
        permissions: list[int],
        until: datetime,
        admin_id: int,
        unlimit=False
) -> dict:
    chat_member = member.get("chat_member_instance")
    user_id = member.get("id")
    username = member.get("username")
    until = get_until_date(until)

    new_permissions = await _parse_permissions(
        context=context,
        permissions=permissions,
        chat_member=chat_member,
        unlimit=unlimit
    )

    limit_methods = [
        ("pyro_username", (lambda: _limit_unlimit_with_pyro(
            context=context,
            user_id=username,
            permissions=new_permissions["pyro_permissions"],
            until_date=until,
            unlimit=unlimit) if username else None)
        ),
        ("pyro_id", lambda: _limit_unlimit_with_pyro(
            context=context,
            user_id=user_id,
            permissions=new_permissions["pyro_permissions"],
            until_date=until,
            unlimit=unlimit)
        ),
        ("ptb", lambda: _limit_unlimit_with_ptb(
            context=context,
            user_id=user_id,
            permissions=new_permissions["pyro_permissions"],
            until_date=until,
            unlimit=unlimit)
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
    actual_permissions = permission_instance_to_dict(actual_permissions)
    if 11 in permissions:
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


async def _limit_unlimit_with_ptb(
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        permissions: PTBChatPermissions,
        until_date: datetime,
        use_independent_chat_permissions=True,
        unlimit=False
) -> bool:
    try:
        await context.bot.restrict_chat_member(
            chat_id=int(context.bot_data["group_chat_id"]),
            user_id=user_id,
            until_date=until_date,
            permissions=permissions,
            use_independent_chat_permissions=use_independent_chat_permissions
        )
        log.info(f"Utente {user_id} {'un' if unlimit else ''}limitato: {permissions}")
        return True
    except TelegramError as e:
        log.error(f"Non è stato possibile {'un' if unlimit else ''}limitare l'utente {user_id} (metodo: PTB): {e}")
        return False


async def _limit_unlimit_with_pyro(
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int | str,
        permissions: PyroChatPermissions,
        until_date: datetime,
        use_independent_chat_permissions=True,
        unlimit=False
) -> bool:
    try:
        await constants.pyro_instance.restrict_chat_member(
            chat_id=int(context.bot_data["group_chat_id"]),
            user_id=add_fucking_at(user_id) if isinstance(user_id, str) else user_id,
            until_date=until_date,
            permissions=permissions,
            use_independent_chat_permissions=use_independent_chat_permissions
        )
        log.info(f"Utente {user_id} {'un' if unlimit else ''}limitato: {permissions}")
        return True
    except Exception as e:
        log.error(f"Non è stato possibile {'un' if unlimit else ''}limitare l'utente {user_id} (metodo: Pyro): {e}")
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


def _compare_permissions(
    old_permissions: Union[PTBChatPermissions, PyroChatPermissions],
    new_permissions: Union[PTBChatPermissions, PyroChatPermissions]
):
    old_permissions = permission_instance_to_dict(old_permissions)
    new_permissions = permission_instance_to_dict(new_permissions)

    diffs = {}

    for el in old_permissions:
        if el not in new_permissions:
            continue
        if old_permissions[el] != new_permissions[el]:
            diffs[el] = new_permissions[el]

    return diffs

async def _log_limit_to_database(
        admin_id: int,
        user_id: int,
        permissions: list[int],
        until: Optional[datetime],
        reason: Optional[str],
        unlimit: bool
):
    try:
        await add_to_table(table_name="limitations", content={
            "admin": admin_id,
            "user_id": user_id,
            "what": permissions,
            "until": until,
            "reason": reason,
            "unlimit": unlimit
        })
    except Exception as e:
        log.error(f"Non è stato possibile loggare l'azione nel database: {e}")


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
    old_permissions = permission_instance_to_dict(old_permissions)
    new_permissions = permission_instance_to_dict(new_permissions)

    permission_text = ""
    sign = "➕" if unlimit else "➖"

    for el in old_permissions:
        if el not in new_permissions:
            continue
        if old_permissions[el] != new_permissions[el]:
            permission_text += f"    {sign} <i>{permissions_texts[el]}</i>\n"

    if not unlimit:
        confirmation_text = f"🔒 Utente {mention} <b>limitato</b> "

        if until_date:
            confirmation_text += f"{format_time_as_rome(until_date)}"

        confirmation_text += "\n\n❓ <u>Permessi Rimossi</u>\n\n"
    else:
        confirmation_text = (f"🔓 Utente {mention} <b>non più limitato</b>.\n\n"
                             f"❓ <u>Permessi Aggiunti</u>\n\n")

    confirmation_text += f"{permission_text}"

    if reason:
        confirmation_text += f"\n<b>Motivo</b>: {reason}\n"

    confirmation_text += "\nℹ <i>Questo messaggio verrà rimosso in 5 minuti</i>."

    return confirmation_text
