# raccoglie tutti i dati che servono al funzionamento del bot

import os

import psycopg
from dotenv import load_dotenv
from telegram.ext import Application

from aimods_bot.modules.exceptions import DatabaseBotException
from loggers import db_logger
from utils import connect_to_database, get_data_from_json

load_dotenv()


async def set_application_data(application: Application):
    """
    Imposta il contenuto di bot_data all'avvio, qualora la persistenza non sia aggiornata.

    Per esempio, se l'elenco admin viene modificato ma, dalla modifica all'arresto del bot, la persistenza non
    si aggiorna (nessun update), l'elenco all'avvio non risulta modificato. Questa funzione sopperisce alla mancanza.
    """
    # noinspection PyNoneFunctionAssignment
    admins = get_admins_from_db()
    if 'admins' not in application.bot_data or application.bot_data["admins"] != admins:
        application.bot_data["admins"] = admins

    group_chat_id = os.getenv("GROUP_CHAT_ID")
    if ('group_chat_id' not in application.bot_data or
            application.bot_data["group_chat_id"] != group_chat_id or
            application.bot_data["group_chat_id"] is None):
        application.bot_data["group_chat_id"] = group_chat_id

    texts = get_data_from_json("texts")

    user_joined_message_text = texts["user_joined_message_text"]
    if ('user_joined_message_text' not in application.bot_data or
            application.bot_data["user_joined_message_text"] != user_joined_message_text):
        application.bot_data["user_joined_message_text"] = user_joined_message_text

    rules_text = texts["rules_text"]
    if 'rules_text' not in application.bot_data or application.bot_data["rules_text"] != rules_text:
        application.bot_data["rules_text"] = rules_text

    application.bot_data["jobs"] = {}


def get_admins_from_db():
    """
    :return: l'elenco corrente di admin all'interno del db
    """
    conn = connect_to_database()
    try:
        res = conn.cursor().execute("SELECT (admin_id, username) from admins").fetchall()
    except psycopg.Error as err:
        DatabaseBotException(f"non è stato possibile reperire la lista degli admin (generic database error)\n\t{err}")
    else:
        db_logger.info("Operation Success: admin list gathered.")
        return {c[0][0]: c[0][1].strip('{}') for c in res}
    finally:
        conn.close()
