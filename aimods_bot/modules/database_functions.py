from psycopg import connect
import psycopg
import telegram
from loggers import db_logger
from constants import Exceptions
import core


async def add_to_table(table_name: str, content: ...):
    if content is None:
        db_logger.error("Content cannot be None")
        return Exceptions.DatabaseException("Content cannot be None")
    if (conn := connect_to_database()) is None:
        db_logger.error("Connection instance is None.")
        raise Exceptions.DatabaseException("Connection instance is None.")

    try:
        conn.cursor().execute(f'INSERT INTO deleted_messages VALUES {generate_values(table_name, content)};')
    except psycopg.Error as e:
        db_logger.error(f'Unable to add entry into \'{table_name}\' table: {e}')
        raise Exceptions.DatabaseException(f'Unable to add entry into \'{table_name}\' table: {e}')
    else:
        db_logger.info(f'Successfully inserted item inside \'{table_name}\'')
        conn.commit()
    finally:
        conn.close()


def generate_values(table_name: str, content_to_elaborate: ...):
    if table_name == "deleted_messages":
        if not isinstance(content_to_elaborate, telegram.Update):
            db_logger.error(f'Cannot elaborate content for inserting entry in table {table_name}: content must be '
                            f'instance of \'telegram.Update\'')
            raise Exceptions.DatabaseException(
                f'Cannot elaborate content for inserting entry in table {table_name}: content must be '
                f'instance of \'telegram.Update\'')
        reason = " ".join(content_to_elaborate.message.text.split(" ")[1:])
        return (f'({content_to_elaborate.message.reply_to_message.id}, '
                f'{content_to_elaborate.effective_user.id}, '
                f'\'{content_to_elaborate.message.date}\', '
                f'{content_to_elaborate.message.reply_to_message.from_user.id}, '
                f'\'{reason if len(reason) != 0 else 'no_reason_given'}\', '
                f'\'{content_to_elaborate.message.reply_to_message.text}\')')


def connect_to_database():
    try:
        conn = connect(core.get_env("POSTGRES_CONNECTION_URL"), client_encoding="utf8")
    except psycopg.Error as e:
        db_logger.error(f'Unable to access database: {e}')
        raise Exceptions.DatabaseException(f'Unable to access database: {e}')
    return conn
