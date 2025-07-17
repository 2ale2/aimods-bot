import os
import asyncpg
from asyncpg import Connection
from typing import Optional, Union

from aimods_bot.src.core.exceptions import DatabaseBotException
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("database")


async def connect_to_database() -> Connection:
    """
    Apre una connessione a PostgreSQL.
    """
    try:
        return await asyncpg.connect(
            os.getenv("POSTGRES_CONNECTION_URL"),
            ssl=False
        )
    except Exception as e:
        raise DatabaseBotException("Errore connessione al database.") from e


async def revoke_last_action(table: str, user_id: int) -> Union[dict, bool, None]:
    """
    Revoca l'ultima azione attiva e non ancora revocata di un utente, se presente.

    Args:
        table: nome della tabella (es. 'bans', 'mutes', ecc.).
        user_id: ID dell'utente.

    Returns:
        dict con i dati dell'azione revocata, oppure None se non c'è nulla da revocare.
    """
    select_query = f"""
            SELECT * FROM {table}
            WHERE user_id = $1
            AND (expires_at IS NULL OR expires_at > now())
            AND revoked_at IS NULL
            ORDER BY issued_at DESC
            LIMIT 1
        """

    rows = await fetch_query(select_query, params=[user_id])
    if not rows:
        return False  # nessuna azione da revocare

    action = dict(rows[0])
    action_id = action["id"]

    success = await revoke_action_by_id(table=table, record_id=action_id)

    if success:
        log.debug(f"✅ Revocata azione '{action_id}' per user {user_id} in '{table}'")
        return action

    log.error(f"Fallita revoca di azione {action_id} in '{table}'")
    return None


async def revoke_action_by_id(table: str, record_id: int) -> bool:
    update_query = f"UPDATE {table} SET revoked_at = now() WHERE id = $1"
    return await execute_query(update_query, params=[record_id])


async def get_columns_order(table_name: str) -> Optional[list[str]]:
    """
    Recupera l'ordine delle colonne di una tabella.
    """
    query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position;
            """
    result = await fetch_query(query, [table_name])

    if result is not None:
        return [row["column_name"] for row in result]

    log.exception(f"❌ Errore nel tentativo di recuperare le colonne di '{table_name}'")
    return None


async def add_to_table(table_name: str, content: dict) -> bool:
    """
    Inserisce una riga nella tabella specificata.
    """
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
        log.info(f"✅ Inserito in {table_name}: {filtered}")
        return True

    log.error(f"❌ Fallito l'inserimento in {table_name}")
    return False


async def execute_query(query: str, params: Optional[list] = None) -> bool:
    """
    Esegue una query arbitraria di tipo EXECUTE (insert/update/delete).
    """
    conn = await connect_to_database()
    try:
        await conn.execute(query, *(params or []))
        log.debug(f"✅ Eseguita: {query} | Params: {params}")
        return True
    except Exception as e:
        log.exception(f"❌ Errore durante l'esecuzione di {query}: {e}")
        return False
    finally:
        await conn.close()


async def fetch_query(query: str, params: Optional[list] = None) -> Optional[list[asyncpg.Record]]:
    """
    Esegue una query di tipo FETCH (select).
    """
    conn = await connect_to_database()
    try:
        result = await conn.fetch(query, *(params or []))
        log.debug(f"📥 Fetched: {len(result)} record(s)")
        return result
    except Exception as e:
        log.exception(f"❌ Errore durante il fetch della query: {e}")
        return None
    finally:
        await conn.close()
