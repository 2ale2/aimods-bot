# raccoglie tutti i dati che servono al funzionamento del bot

import os

from dotenv import load_dotenv
from telegram.ext import Application

from utils import get_data_from_json

load_dotenv()


async def set_application_data(application: Application):
    """
    Imposta il contenuto di bot_data all'avvio, qualora la persistenza non sia aggiornata.

    Per esempio, se l'elenco admin viene modificato ma, dalla modifica all'arresto del bot, la persistenza non
    si aggiorna (nessun update), l'elenco all'avvio non risulta modificato. Questa funzione sopperisce alla mancanza.
    """
    group_chat_id = os.getenv("GROUP_CHAT_ID")
    if ('group_chat_id' not in application.bot_data or
            application.bot_data["group_chat_id"] != group_chat_id or
            application.bot_data["group_chat_id"] is None):
        application.bot_data["group_chat_id"] = group_chat_id

    # noinspection PyNoneFunctionAssignment
    admins = await get_admins(application)
    if 'admins' not in application.bot_data or application.bot_data["admins"] != admins:
        application.bot_data["admins"] = admins

    texts = get_data_from_json("texts")

    user_joined_message_text = texts["user_joined_message_text"]
    if ('user_joined_message_text' not in application.bot_data or
            application.bot_data["user_joined_message_text"] != user_joined_message_text):
        application.bot_data["user_joined_message_text"] = user_joined_message_text

    rules_text = texts["rules_text"]
    if 'rules_text' not in application.bot_data or application.bot_data["rules_text"] != rules_text:
        application.bot_data["rules_text"] = rules_text

    application.bot_data["jobs"] = {}


async def get_admins(app: Application):
    """
    :return: l'elenco corrente di admin della chat
    """
    admins = await app.bot.get_chat_administrators(chat_id=app.bot_data["group_chat_id"])
    admins_dict = {}

    for admin in admins:
        user = admin["user"]
        admins_dict[str(user.id)] = user.name

    return admins_dict
