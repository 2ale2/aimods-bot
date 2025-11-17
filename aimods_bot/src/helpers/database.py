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


def validate_table_name(table: str) -> str:
    """
    Valida il nome della tabella contro la whitelist.

    Args:
        table: Nome della tabella da validare.

    Returns:
        Il nome della tabella se valido.

    Raises:
        DatabaseBotException: Se la tabella non è nella whitelist.
    """
    if table not in ALLOWED_TABLES:
        raise DatabaseBotException(f"Tabella non valida: {table}")
    return table


async def revoke_last_action(table: TableName, user_id: int) -> Union[Dict[str, Any], bool, None]:
    """
    Revoca l'ultima azione attiva e non ancora revocata di un utente, se presente.
    Usa transazioni per garantire atomicità.

    Args:
        table: Nome della tabella (es. 'bans', 'mutes', ecc.).
        user_id: ID dell'utente.

    Returns:
        dict con i dati dell'azione revocata, False se non c'è nulla da revocare,
        None in caso di errore.
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

                success = await revoke_action_by_id(table=table, record_id=action_id)

                if success:
                    log.debug(f"✅ Revocata azione '{action_id}' per user {user_id} in '{table}'")
                    return action

                log.error(f"Fallita revoca di azione {action_id} in '{table}'")
                return None

    except Exception as e:
        log.exception(f"Errore durante revoca azione in '{table}': {e}")
        return None


async def revoke_action_by_id(table: TableName, record_id: int) -> bool:
    """
    Revoca un'azione specifica per ID.

    Args:
        table: Nome della tabella.
        record_id: ID del record da revocare.

    Returns:
        True se l'operazione è riuscita, False altrimenti.
    """
    table = validate_table_name(table)
    update_query = f"UPDATE {table} SET revoked_at = now() WHERE id = $1"
    return await execute_query(update_query, params=[record_id])


async def get_columns_order(table_name: str) -> Optional[List[str]]:
    """
    Recupera l'ordine delle colonne di una tabella.

    Args:
        table_name: Nome della tabella.

    Returns:
        Lista di nomi delle colonne ordinati, o None in caso di errore.
    """
    query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position; \
            """
    result = await fetch_query(query, [table_name])

    if result is not None:
        return [row["column_name"] for row in result]

    log.exception(f"❌ Errore nel tentativo di recuperare le colonne di '{table_name}'")
    return None


async def add_to_table(table_name: TableName, content: Dict[str, Any]) -> bool:
    """
    Inserisce una riga nella tabella specificata.

    Args:
        table_name: Nome della tabella.
        content: Dizionario con i dati da inserire.

    Returns:
        True se l'inserimento è riuscito, False altrimenti.

    Raises:
        DatabaseBotException: Se il contenuto non è valido.
    """
    table_name = validate_table_name(table_name)

    if not isinstance(content, dict) or not content:
        raise DatabaseBotException("Il contenuto deve essere un dizionario non vuoto.")

    columns_order = await get_columns_order(table_name)
    if not columns_order:
        raise DatabaseBotException(f"Impossibile recuperare colonne per '{table_name}'.")

    filtered = {col: content[col] for col in columns_order if col in content}
    if not filtered:
        raise DatabaseBotException(f"Nessuna colonna valida trovata per '{table_name}'.")

    columns = list(filtered.keys())
    values = list(filtered.values())
    placeholders = ', '.join(f"${i + 1}" for i in range(len(values)))

    query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
    success = await execute_query(query, list(filtered.values()))

    if success:
        log.info(f"Inserito in {table_name}: {filtered}")
        return True

    log.warning(f"Fallito l'inserimento in {table_name}")
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
async def execute_query(query: str, params: Optional[List[Any]] = None) -> bool:
    """
    Esegue una query arbitraria di tipo EXECUTE (insert/update/delete).
    Include retry logic per errori transitori di connessione.

    Args:
        query: Query SQL da eseguire.
        params: Parametri della query.

    Returns:
        True se l'esecuzione è riuscita, False altrimenti.
    """
    try:
        async with get_connection() as conn:
            await conn.execute(query, *(params or []))
            log.debug(f"Eseguita: {query} | Params: {params}")
            return True
    except UniqueViolationError:
        log.warning(
            f"Constraint violated: unique constraint. "
            f"NOTE — If the query was inserting into 'recap_posts' this shouldn't be a problem."
        )
        return False
    except Exception as e:
        log.exception(f"Errore durante l'esecuzione di {query}: {e}")
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
async def fetch_query(query: str, params: Optional[List[Any]] = None) -> Optional[List[asyncpg.Record]]:
    """
    Esegue una query di tipo FETCH (select).
    Include retry logic per errori transitori di connessione.

    Args:
        query: Query SQL da eseguire.
        params: Parametri della query.

    Returns:
        Lista di record o None in caso di errore.
    """
    try:
        async with get_connection() as conn:
            result = await conn.fetch(query, *(params or []))
            log.debug(f"Fetched: {len(result)} record(s)")
            return result
    except Exception as e:
        log.exception(f"Errore durante il fetch della query: {e}")
        return None