import asyncpg
from asyncpg import UniqueViolationError
from typing import Optional, Union, Dict, Any, List, Literal
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from aimods_bot.src.core.exceptions import DatabaseBotException
from aimods_bot.src.core.database_pool import get_connection
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("database")

ALLOWED_TABLES = {'persistence', 'persistence_test', 'requests', 'recap_posts', 'requests_posts'}

TableName = Literal['persistence', 'persistence_test', 'requests', 'recap_posts', 'requests_posts']

_COLUMNS_CACHE: Dict[str, List[str]] = {}


def validate_table_name(table: str) -> str:
    if table not in ALLOWED_TABLES:
        raise DatabaseBotException(f"Tabella non valida: {table}")
    return table


async def revoke_last_action(table: TableName, user_id: int) -> Union[Dict[str, Any], bool, None]:
    """
    Revoca l'ultima azione attiva e non ancora revocata di un utente, se presente.
    Usa transazioni per garantire atomicità.
    """
    table = validate_table_name(table)

    try:
        async with get_connection() as conn:
            async with conn.transaction():
                select_query = f"""
                    SELECT * FROM {table}
                    WHERE user_id = $1
                    AND (expires_at IS NULL OR expires_at > now())
                    AND revoked_at IS NULL
                    ORDER BY issued_at DESC
                    LIMIT 1
                    FOR UPDATE
                """

                rows = await conn.fetch(select_query, user_id)

                if not rows:
                    return False  # Nessuna azione da revocare

                action = dict(rows[0])
                action_id = action["id"]

                update_query = f"UPDATE {table} SET revoked_at = now() WHERE id = $1"
                await conn.execute(update_query, action_id)

                log.debug(f"✅ Revocata azione '{action_id}' per user {user_id} in '{table}'")
                return action

    except Exception as e:
        log.exception(f"Errore durante revoca azione in '{table}': {e}")
        return None


async def revoke_action_by_id(table: TableName, record_id: int) -> bool:
    """
    Revoca un'azione specifica per ID.
    """
    table = validate_table_name(table)
    update_query = f"UPDATE {table} SET revoked_at = now() WHERE id = $1"
    return await execute_query(update_query, params=[record_id])


async def get_columns_order(table_name: str) -> Optional[List[str]]:
    """
    Recupera l'ordine delle colonne di una tabella.
    """
    if table_name in _COLUMNS_CACHE:
        return _COLUMNS_CACHE[table_name]

    query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position; \
            """
    result = await fetch_query(query, [table_name])

    if result is not None:
        columns = [row["column_name"] for row in result]
        _COLUMNS_CACHE[table_name] = columns
        return columns

    log.exception(f"Errore nel tentativo di recuperare le colonne di '{table_name}'")
    return None


async def add_to_table(table_name: TableName, content: Dict[str, Any]) -> bool:
    """
    Inserisce una riga nella tabella specificata.
    """
    table_name = validate_table_name(table_name)

    if not isinstance(content, dict) or not content:
        raise DatabaseBotException("Il contenuto deve essere un dizionario non vuoto.")

    columns_order = await get_columns_order(table_name)
    if not columns_order:
        raise DatabaseBotException(f"Impossibile recuperare colonne per '{table_name}'.")

    filtered = {col: content[col] for col in columns_order if col in content}
    if not filtered:
        log.warning(
            f"Nessuna colonna valida trovata per inserimento in '{table_name}'. Input keys: {list(content.keys())}"
        )
        return False

    columns = list(filtered.keys())
    values = list(filtered.values())
    placeholders = ', '.join(f"${i + 1}" for i in range(len(values)))

    query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

    return await execute_query(query, values)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((
            asyncpg.PostgresConnectionError,
            asyncpg.TooManyConnectionsError,
            asyncpg.CannotConnectNowError,
    )),
    reraise=True
)
async def _execute_query_internal(query: str, params: list):
    """
    Tenacity intercetta l'errore e riprova.
    """
    async with get_connection() as conn:
        await conn.execute(query, *(params or []))


async def execute_query(query: str, params: Optional[List[Any]] = None) -> bool:
    try:
        await _execute_query_internal(query, params)
        log.debug(f"Eseguita: {query}")
        return True

    except UniqueViolationError:
        log.warning("Violazione vincolo unique.")
        return False

    except Exception as e:
        log.exception(f"Fallimento definitivo query dopo retry: {e}")
        return False


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((
            asyncpg.PostgresConnectionError,
            asyncpg.TooManyConnectionsError,
            asyncpg.CannotConnectNowError,
    )),
    reraise=True
)
async def _fetch_query_internal(query: str, params: list) -> List[asyncpg.Record]:
    """
    Tenacity intercetta l'errore e riprova.
    """
    async with get_connection() as conn:
        return await conn.fetch(query, *(params or []))


async def fetch_query(query: str, params: Optional[List[Any]] = None) -> Optional[List[asyncpg.Record]]:
    try:
        result = await _fetch_query_internal(query, params or [])

        log.debug(f"Fetched: {len(result)} record(s)")
        return result
    except Exception as e:
        log.exception(f"Errore definitivo fetch_query dopo retry: {e}")
        return None
