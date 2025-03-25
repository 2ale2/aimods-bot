import os.path

from psycopg import connect
import pytz
import psycopg
import telegram
from telegram import Update

from loggers import db_logger

from exceptions import DatabaseBotException


async def add_to_table(table_name: str, content: dict):
    """
    Aggiunge entry al database. L'ordine delle colonne deve essere rispettato (vedi la documentazione).
    :param table_name: il nome della tabella
    :param content: dizionario del tipo {'colonna 1': 'valore 1')
    :return:
    """

    columns = content.keys()
    values = content.values()

    if table_name == "admins":
        query = f"INSERT INTO admins ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(values))})"

    # if content is None:
    #     db_logger.error("Content cannot be None")
    #     return DatabaseBotException("Content cannot be None")
    # if (conn := connect_to_database()) is None:
    #     db_logger.error("Connection instance is None.")
    #     raise DatabaseBotException("Connection instance is None.")
    #
    # try:
    #     conn.cursor().execute("INSERT INTO deleted_messages VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
    #                           await generate_values('deleted_messages', content))
    # except psycopg.Error as e:
    #     db_logger.error(f'Unable to add entry into \'{table_name}\' table: {e}')
    #     raise DatabaseBotException(f'Unable to add entry into \'{table_name}\' table: {e.__repr__()}')
    # else:
    #     db_logger.info(f'Successfully inserted item inside \'{table_name}\'')
    #     conn.commit()
    # finally:
    #     conn.close()


async def generate_values(table_name: str, content_to_elaborate: Update):
    if table_name == "deleted_messages":
        if not isinstance(content_to_elaborate, telegram.Message):
            db_logger.error(f'Cannot elaborate content for inserting entry in table {table_name}: content must be '
                            f'instance of \'telegram.Message\'')
            raise DatabaseBotException(
                f'Cannot elaborate content for inserting entry in table {table_name}: content must be '
                f'instance of \'telegram.Message\'')
        reason = " ".join(content_to_elaborate.message.text.split(" ")[1:])
        if len(reason) == 0:
            reason = '\"no reason given\"'
        message_id_to_delete = content_to_elaborate.message.reply_to_message.id
        admin_performing_the_action = content_to_elaborate.effective_user.id
        message_date = str(content_to_elaborate.message.date.astimezone(pytz.timezone('Etc/GMT-2')))
        message_author = content_to_elaborate.message.reply_to_message.from_user.id

        if attachment := content_to_elaborate.message.reply_to_message.effective_attachment:
            file_sent = await attachment[-1].get_file()
            if not os.path.isdir(os.path.join('database', 'removed_attachments', 'photos')):
                os.makedirs(os.path.join('database', 'removed_attachments', 'photos'))
            path_to_file = await file_sent.download_to_drive(
                custom_path=os.path.join('database', 'removed_attachments', 'photos',
                                         f'{file_sent.file_unique_id}.png'),
            )
            path_to_file = path_to_file.parts[-1]
        else:
            path_to_file = None
        if content_to_elaborate.message.reply_to_message.text:
            message_content = content_to_elaborate.message.reply_to_message.text
        else:
            message_content = None
        author_username = content_to_elaborate.message.reply_to_message.from_user.name
        return (message_id_to_delete,
                admin_performing_the_action,
                message_date,
                message_author,
                reason,
                message_content,
                author_username,
                path_to_file)


async def get_attachment_string_to_store(attachment):
    pass


def connect_to_database():
    try:
        conn = connect(os.getenv("POSTGRES_CONNECTION_URL"), client_encoding="utf8")
    except psycopg.Error as e:
        db_logger.error(f'Unable to access database: {e}')
        raise DatabaseBotException(f'Unable to access database: {e}')
    return conn
