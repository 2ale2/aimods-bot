from telegram.ext import ContextTypes
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import resolve_chat_member
from telegram.constants import ChatMemberStatus as ChatMemberStatusPTB
from pyrogram.enums import ChatMemberStatus as ChatMemberStatusPyro

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


async def user_is_banned(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool | None:
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


async def get_user_warnings(user_id: int) -> int | None:
    """
    Restituisce il numero di warning attivi per un utente.

    Args:
        user_id: ID utente.

    Returns:
        Intero con il numero di warning attivi, oppure None in caso di errore.
    """
    query = """
        SELECT COUNT(*) AS count
        FROM warnings
        WHERE user_id = $1
        AND (expires_at IS NULL OR expires_at > now())
        AND revoked_at IS NULL
    """
    result = await fetch_query(query=query, params=[user_id])

    if not result:
        log.error(f"❌ Impossibile ottenere i warnings per user_id={user_id}")
        return None

    return dict(result[0])["count"]
