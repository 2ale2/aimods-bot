from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Union, Callable, Awaitable, Any

from pyrogram.types import ChatMember as PyroChatMember, ChatPermissions as PyroChatPermissions, User as PyroUser
from telegram import ChatMember as PTBChatMember, ChatPermissions as PTBChatPermissions, User as PTBUser
from telegram.ext import ConversationHandler

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import MissingParameterException
from aimods_bot.src.helpers.constants.permissions import default_permissions, get_pyro_permissions, get_ptb_permissions
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.chat_utils import get_chat_permissions
from aimods_bot.src.helpers.utils.telegram_utils import resolve_chat_member, add_fucking_at, is_user_id, resolve_user, \
    get_banned_panel, safe_delete

log = logger.getChild("user_utils")

_member_cache = {}
_cache_ttl = timedelta(minutes=5)


async def get_globally_cached_member(context: CustomContext, user_id: int, chat_id: int = None):
    """Cache i membri per ridurre chiamate API ripetute"""
    cache_key = f"{chat_id}:{user_id}"
    cached = _member_cache.get(cache_key)

    if cached and datetime.now() - cached['timestamp'] < _cache_ttl:
        return cached['data']
    else:
        del _member_cache[cache_key]

    response = await resolve_chat_member(context=context, user_identifier=user_id, chat_id=chat_id)

    _member_cache[cache_key] = {
        'data': response,
        'timestamp': datetime.now()
    }

    return response


async def get_or_resolve_user(context: CustomContext, identifier: Union[str, int]):
    """
    Tenta di recuperare un oggetto utente (ChatMember/User) dato un ID o Username.
    Gestisce automaticamente la cache 'ephemeral.resolved_users'.
    Ritorna None se l'utente non esiste o non può essere risolto.
    """
    if isinstance(identifier, str) and identifier.isdigit():
        identifier = int(identifier)

    str_id = str(identifier)
    cache = context.pydc.ephemeral.resolved_users

    if str_id in cache:
        res = cache[str_id]
        if isinstance(res, dict) and "user" in res:
            return res["user"]
        return res

    user_response = await resolve_user(identifier=identifier)

    context.pydc.ephemeral.resolved_users[str_id] = user_response

    if user_response["status"] == "success":
        return user_response["user"]

    return None  # Può avere senso perché eventuali errori sono già loggati in resolve_user


async def is_admin(user_id: int, context: CustomContext) -> bool:
    """
    Verifica se l'utente è un admin del gruppo.
    """
    return user_id in list(context.pydb.admins.keys())


async def user_in_chat(user_id: int, context: CustomContext, chat_id: int = None) -> bool:
    """
    Verifica se l'utente è attualmente nella chat.
    Ritorna False in caso di errore.
    """
    try:
        response = await get_globally_cached_member(context=context, user_id=user_id, chat_id=chat_id)

        if response["status"] == "failed":
            log.error(f"Failed to resolve user {user_id}: {response.get('error')}")
            return False

        member = response["member"]
        return member.status not in ("left", "kicked")

    except Exception as e:
        log.exception(f"Unexpected error checking user {user_id} in chat: {e}")
        return False


async def user_is_banned(context: CustomContext, user_id: Union[int, str], chat_id: int = None) -> bool:
    """
    Verifica se l'utente è bannato (o presente in una lista ban).
    Ritorna False in caso di errore.
    """
    if str(user_id) in context.pydb.ban_list:
        return True

    try:
        response = await get_globally_cached_member(context=context, user_id=user_id, chat_id=chat_id)

        if response["status"] == "failed":
            log.warning(f"Cannot resolve user {user_id}: {response.get('error')}")
            return False

        member = response["member"]
        return member.status.value in ("banned", "kicked")

    except Exception as e:
        log.exception(f"Error checking ban status for {user_id}: {e}")
        return False


async def get_user_warnings(user_id: int) -> dict[int, dict]:
    """
    Restituisce gli warning attivi per un utente.
    Ritorna dict vuoto in caso di errore o nessun warning.
    """
    query = """
            SELECT *
            FROM warnings
            WHERE user_id = $1
              AND (expires_at IS NULL OR expires_at > now())
              AND revoked_at IS NULL
            ORDER BY issued_at DESC \
            """

    try:
        result = await fetch_query(query=query, params=[user_id])
        return {i: result[i] for i in range(len(result))} if result else {}

    except Exception as e:
        log.exception(f"Database error fetching warnings for user {user_id}: {e}")
        return {}


async def get_user_warnings_count(user_id: int) -> int:
    """
    Restituisce il numero di warning attivi per un utente.
    """
    query = """
            SELECT COUNT(*) as count
            FROM warnings
            WHERE user_id = $1
              AND (expires_at IS NULL OR expires_at > now())
              AND revoked_at IS NULL \
            """

    try:
        result = await fetch_query(query=query, params=[user_id])
        return result[0]['count'] if result else 0

    except Exception as e:
        log.exception(f"Error counting warnings for user {user_id}: {e}")
        return 0


async def erase_user_warnings(user_id: int) -> Optional[list[str]]:
    """
    Cancella tutti i warning attivi per un utente.
    Usa una singola query batch invece di N query separate.
    """
    warnings = await get_user_warnings(user_id=user_id)
    if not warnings:
        return None

    warning_ids = [record["id"] for record in warnings.values()]

    # Singola query batch
    query = """
            UPDATE warnings
            SET revoked_at = now()
            WHERE id = ANY ($1)
            RETURNING id \
            """

    try:
        result = await fetch_query(query=query, params=[warning_ids])
        revoked_ids = {str(r['id']) for r in result} if result else set()
        failed_ids = [str(wid) for wid in warning_ids if str(wid) not in revoked_ids]
        return failed_ids if failed_ids else None

    except Exception as e:
        log.exception(f"Error revoking warnings for user {user_id}: {e}")
        return [str(wid) for wid in warning_ids]


async def get_member_permissions(
        context: CustomContext,
        chat_member: Union[PyroChatMember, PTBChatMember],
) -> Union[PTBChatPermissions, PyroChatPermissions]:
    """
    Ottiene i permessi effettivi di un membro.
    """
    is_pyro = isinstance(chat_member, PyroChatMember)
    status = chat_member.status.value if is_pyro else chat_member.status

    if is_pyro and status == "restricted":
        return chat_member.permissions

    if status == "owner":
        return get_pyro_permissions(True) if is_pyro else get_ptb_permissions(True)

    if status in ("restricted", "administrator"):
        permissions_dict = {
            attr: getattr(chat_member, attr)
            for attr in default_permissions.keys()
            if hasattr(chat_member, attr) and isinstance(getattr(chat_member, attr), bool)
        }
        return (PyroChatPermissions if is_pyro else PTBChatPermissions)(**permissions_dict)

    chat_perms = await get_chat_permissions(context=context, chat_id=context.pydb.group_chat_id)
    return PyroChatPermissions(**chat_perms.to_dict()) if is_pyro else chat_perms


async def get_member_details_text(
        context: Optional[CustomContext] = None,
        user_identifier: Optional[Union[int, str]] = None,
        user: Optional[Union[PTBChatMember, PyroChatMember, PyroUser, PTBUser]] = None
) -> str:
    if not user_identifier and not user:
        raise MissingParameterException("You must provide at least 'user' or 'user_identifier'.")

    if not user and context:
        resolved = context.pydc.ephemeral.resolved_users
        resolving_attempt = resolved.get(str(user_identifier), False)
        if resolving_attempt is None:  # User has not been resolved yet
            resolving_attempt = await resolve_user(identifier=user_identifier)
            resolved[str(user_identifier)] = resolving_attempt["user"]

    if user:
        if isinstance(user, Union[PTBChatMember, PyroChatMember]):
            user = user.user
        text = (f"     🆔 <b>User ID</b> – <code>{user.id}</code>\n"
                f"     🪪 <b>Nome</b> – {user.first_name}\n")
        if user.username:
            text += f"     🔖 <b>Username</b> – {add_fucking_at(user.username)}\n"
    else:
        if is_user_id(user_identifier):
            text = f"     🆔 <b>User ID</b> – <code>{user_identifier}</code>\n"
        else:  # is_username
            text = f"     🔖 <b>Username</b> – {add_fucking_at(user_identifier)}\n"

    return text


async def _show_ban_panel(update, context: CustomContext):
    """Helper interno per mostrare il pannello ban"""
    await safe_delete(update=update, context=context)
    panel = get_banned_panel()
    await panel.render(update=update, context=context)


def check_auth(n: int = 5, bypass_count: bool = False):
    """
    Decoratore per controllo auth e ban.
    - Ogni N interazioni esegue il controllo ban.
    - Se bannato: mostra pannello e return ConversationHandler.END
    - Altrimenti: resetta il contatore a 0 e continua.
    - Negli altri casi: incrementa il contatore e continua.

    Parametri:
      n: ogni quante interazioni effettuare il controllo (default 5)
      bypass_count: se True, esegue sempre il controllo
    """

    def decorator(handler: Callable[..., Awaitable[Any]]):
        @wraps(handler)
        async def wrapper(update, context, *args, **kwargs):
            mc = context.pydu.persistent.member_check

            if not bypass_count and mc < (n - 1):
                context.pydu.persistent.member_check = mc + 1
                return await handler(update, context, *args, **kwargs)

            context.pydu.persistent.member_check = 0

            user = update.effective_user
            user_id = user.username or user.id

            try:
                if await user_is_banned(context=context, user_id=user_id):
                    await _show_ban_panel(update, context)
                    return ConversationHandler.END
            except Exception as e:
                log.warning(f"Ban check failed for {user_id}: {e}")

            return await handler(update, context, *args, **kwargs)

        return wrapper

    return decorator
