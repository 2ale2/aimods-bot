# raccoglie tutti i dati che servono al funzionamento del bot

import json
import os
import psycopg
from dotenv import load_dotenv
from telegram.ext import Application

from loggers import db_logger

load_dotenv()


def get_env(env: str):
    """
    :param env:  nome variabile ambiente
    :return:    contenuto della variabile ambiente
    """
    return os.getenv(env)


async def set_application_data(application: Application):
    """
    Imposta il contenuto di bot_data all'avvio, qualora la persistenza non sia aggiornata.

    Per esempio, se l'elenco admin viene modificato ma, dalla modifica all'arresto del bot, la persistenza non
    si aggiorna (nessun update), l'elenco all'avvio non risulta modificato. Questa funzione sopperisce alla mancanza.
    """
    admins = get_admins_from_db()
    if 'admins' not in application.bot_data or application.bot_data["admins"] != admins:
        application.bot_data["admins"] = admins


def get_topics_from_json():
    """
    :return:    i topic del forum (tutti e categorie)
    """
    with open("../misc/data.json", "r") as fp:
        topics = json.load(fp)
        return topics["forum_topics"]


def get_admins_from_db():
    """
    :return: l'elenco corrente di admin all'interno del db
    """
    conn = connect()
    try:
        res = conn.cursor().execute("SELECT (admin_id, username) from admins").fetchall()
    except psycopg.Error as err:
        db_logger.error(f"Unable to collect (admin_id, username) from admins table: {err}")
    else:
        db_logger.info("Operation Success: information gathered.")
        return {c[0][0]: c[0][1] for c in res}
    finally:
        conn.close()


def connect():
    try:
        conn = psycopg.connect(get_env("POSTGRES_CONNECTION_URL"))
    except psycopg.Error as err:
        db_logger.error(f"Unable to connect to database: {err}")
    else:
        return conn
