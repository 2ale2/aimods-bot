import os.path

import psycopg
from psycopg import connect

from aimods_bot.modules.loggers import bot_logger
from exceptions import DatabaseBotException
from loggers import db_logger


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
    WHERE table_name = %s
    ORDER BY ordinal_position;
    """
    async with conn.cursor() as cursor:
        try:
            await cursor.execute(query, (table_name,))
            result = await cursor.fetchall()
            return [row[0] for row in result]
        except psycopg.Error as e:
            db_logger.error(e)
            raise DatabaseBotException(e)


async def add_to_table(table_name: str, content: dict):
    """
    Aggiunge entry al database.
    :param table_name: il nome della tabella
    :param content: dizionario del tipo {'colonna 1': 'valore 1'}
    :return:
    """
    async with connect_to_database() as conn:
        try:
            columns_order = await get_columns_order(conn, table_name)
            ordered_content = {col: content[col] for col in columns_order if col in content}
            if not ordered_content:
                raise DatabaseBotException("'content' non contiene colonne valide.")

            columns = ordered_content.keys()
            values = ordered_content.values()

            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(values))})"

            async with conn.cursor() as cursor:
                await cursor.execute(query, tuple(values))
                await conn.commit()
        except Exception as e:
            await conn.rollback()
            db_logger.error(f"Errore durante l'inserimento in {table_name}: ", e)
            bot_logger.error("Errore nel database. Vedi i log del database.")
            raise


def connect_to_database():
    conn = None
    try:
        conn = connect(os.getenv("POSTGRES_CONNECTION_URL"), client_encoding="utf8")
        yield conn
    except psycopg.Error as e:
        db_logger.error(f'Unable to access database: {e}')
        raise DatabaseBotException(f'Unable to access database: {e}')
    finally:
        if conn is not None:
            conn.close()
