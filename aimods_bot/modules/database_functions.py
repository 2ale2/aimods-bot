import os.path

import asyncpg

from exceptions import DatabaseBotException
from loggers import db_logger, bot_logger


async def get_columns_order(conn, table_name: str):
    """
    Recupera l'ordine delle colonne dal database.
    :param conn: connessione al database
    :param table_name: nome della tabella
    :return: lista dei nomi delle colonne ordinate
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
        db_logger.error(e)
        raise DatabaseBotException(e)


async def add_to_table(table_name: str, content: dict):
    """
    Aggiunge entry al database.
    :param table_name: il nome della tabella
    :param content: dizionario del tipo {'colonna 1': 'valore 1'}
    :return:
    """
    conn = await connect_to_database()
    try:
        columns_order = await get_columns_order(conn, table_name)
        ordered_content = {col: content[col] for col in columns_order if col in content}
        if not ordered_content:
            raise DatabaseBotException("'content' non contiene colonne valide.")

        columns = ordered_content.keys()
        values = ordered_content.values()
        query = (f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES "
                 f"({', '.join([f'${i+1}' for i in range(len(values))])})")

        await conn.execute(query, *values)
    except Exception as e:
        db_logger.error(f"Errore durante l'inserimento in {table_name}: {e}")
        bot_logger.error("Errore nel database. Vedi i log del database.")
        raise
    finally:
        await conn.close()


async def execute_query(query: str, for_value=False, params=None):
    conn = await connect_to_database()
    try:
        if for_value:
            result = await conn.fetch(query, *params) if params else await conn.fetch(query)
        else:
            await conn.execute(query, *params) if params else await conn.execute(query)
            result = True
    except Exception as e:
        db_logger.error(f"Errore durante l'esecuzione di {query}: {e}")
        bot_logger.error("Errore nel database. Vedi i log del database.")
        return None
    else:
        return result
    finally:
        await conn.close()


async def connect_to_database():
    try:
        conn = await asyncpg.connect(os.getenv("POSTGRES_CONNECTION_URL"), ssl=False)
        return conn
    except Exception as e:
        db_logger.error(f'Unable to access database: {e}')
        raise DatabaseBotException(f'Unable to access database: {e}')
