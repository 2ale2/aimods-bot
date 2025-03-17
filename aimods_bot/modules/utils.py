import json
import os
import psycopg

from aimods_bot.modules.loggers import db_logger


def get_env(env: str):
    """
    :param env:  nome variabile ambiente
    :return:    contenuto della variabile ambiente
    """
    return os.getenv(env)


def get_data_from_json(data: str):
    """
    :return:    il contenuto del file di configurazione json richiesto
    """
    with open("aimods_bot/misc/data.json", encoding="utf-8", mode="r") as fp:
        content = json.load(fp)
        return content[data]


async def get_file(file):
    try:
        iter(file)
    except TypeError:
        return file.get_file()
    else:
        await get_file(file[-1])


def connect_to_database():
    try:
        conn = psycopg.connect(get_env("POSTGRES_CONNECTION_URL"), client_encoding="utf8")
    except psycopg.Error as e:
        db_logger.error(f'Unable to access database: {e}')
        raise psycopg.Error(f'Unable to access database: {e}')
    return conn
