from typing import Optional
from pyrogram.enums import ChatMemberStatus as ChatMemberStatusPyro
from telegram.constants import ChatMemberStatus as ChatMemberStatusPTB
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.database import fetch_query, revoke_action_by_id
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import resolve_chat_member

log = logger.getChild("user_utils")


async def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Verifica se l'utente è un admin del gruppo.
    """
    return str(user_id) in context.bot_data["admins"].keys()


async def user_in_chat(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Verifica se l'utente è attualmente nella chat.
    """
    member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    return member.status not in ("left", "kicked")


async def user_is_banned(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> Optional[bool]:
    """Verifica se l'utente è bannato (o presente in una lista ban)."""

    ban_list = context.bot_data.get("ban_list", {})
    if str(user_id) in ban_list:
        return True

    response = await resolve_chat_member(context, user_id)
    if response["status"] == "failed":
        log.warning(f"Errore nel parsing dell'utente {user_id}: {response['error']}. Vedi i log.")
        return None
    member = response["member"]

    return member.status == ChatMemberStatusPTB.BANNED or member.status == ChatMemberStatusPyro.BANNED


async def erase_user_warnings(user_id: int) -> Optional[list[str]]:
    warnings = await get_user_warnings(user_id=user_id)
    if not warnings:
        return None

    errors = []
    for el in warnings:
        record = warnings[el]
        response = await revoke_action_by_id(table="warnings", record_id=record["id"])
        if not response:
            errors.append(str(record["id"]))

    return errors


async def get_user_warnings(user_id: int) -> Optional[dict]:
    """Restituisce gli warning attivi per un utente."""

    query = """
        SELECT *
        FROM warnings
        WHERE user_id = $1
        AND (expires_at IS NULL OR expires_at > now())
        AND revoked_at IS NULL
    """
    result = await fetch_query(query=query, params=[user_id])

    if len(result) == 0:
        return {}

    if result is None:
        log.error(f"❌ Impossibile ottenere i warnings per user_id={user_id}")
        return None

    return {i: result[i] for i in range(0, len(result))}


async def get_user_warnings_count(user_id: int) -> Optional[int]:
    """Restituisce il numero di warning attivi per un utente."""

    response = await get_user_warnings(user_id=user_id)

    return len(response) if response is not None else None
