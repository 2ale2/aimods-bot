import os
import asyncpg

from exceptions import DatabaseBotException
from loggers import db_logger, bot_logger
from asyncpg import Connection


async def connect_to_database() -> Connection:
    try:
        return await asyncpg.connect(
            os.getenv("POSTGRES_CONNECTION_URL"),
            ssl=False
        )
    except Exception as e:
        db_logger.exception("Unable to access database")
        raise DatabaseBotException(f"Unable to access database: {e}")


async def get_columns_order(conn: Connection, table_name: str) -> list[str]:
    """
    Recupera l'ordine delle colonne dal database.
    """
    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position;
    """
    try:
        result = await conn.fetch(query, table_name)
        return [row['column_name'] for row in result]
    except Exception as e:
        db_logger.exception(f"Errore ottenendo le colonne per {table_name}")
        raise DatabaseBotException(f"Errore ottenendo colonne: {e}")


async def add_to_table(table_name: str, content: dict):
    """
    Aggiunge una entry a una tabella del database.
    """
    if not isinstance(content, dict) or not content:
        raise ValueError("Il contenuto da inserire deve essere un dizionario non vuoto.")

    conn = await connect_to_database()
    try:
        columns_order = await get_columns_order(conn, table_name)
        ordered_content = {col: content[col] for col in columns_order if col in content}

        if not ordered_content:
            raise DatabaseBotException(f"'content' non contiene colonne valide per {table_name}.")

        columns = list(ordered_content.keys())
        values = list(ordered_content.values())
        placeholders = ', '.join(f"${i+1}" for i in range(len(values)))

        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        await conn.execute(query, *values)

    except Exception as e:
        db_logger.exception(f"Errore durante l'inserimento in {table_name}")
        bot_logger.error("Errore nel database. Vedi i log del database.")
        raise
    finally:
        await conn.close()


async def execute_query(query: str, for_value=False, params: list = None):
    """
    Esegue una query generica sul database.
    """
    async with await connect_to_database() as conn:
        try:
            if for_value:
                return await conn.fetch(query, *params) if params else await conn.fetch(query)
            else:
                await conn.execute(query, *params) if params else await conn.execute(query)
                return True
        except Exception as e:
            db_logger.exception(f"Errore durante l'esecuzione della query: {query}")
            bot_logger.error("Errore nel database. Vedi i log del database.")
            return None
