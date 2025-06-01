# raccoglie tutti i dati che servono al funzionamento del bot

import os

from dotenv import load_dotenv
from telegram.ext import Application
from pyrogram import Client
from pyrogram.errors import RPCError

from automatic_tasks import create_and_send_recaps
from loggers import bot_logger
from utils import get_data_from_json, get_time_until_next_recap
from datetime import timedelta

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

    commands = get_data_from_json("commands")
    if 'commands' not in application.bot_data or application.bot_data["commands"] != commands:
        application.bot_data["commands"] = commands

    hashtags = get_data_from_json("hashtags")
    if 'hashtags' not in application.bot_data or application.bot_data["hashtags"] != hashtags:
        application.bot_data["hashtags"] = hashtags

    autorecap_job_name = "auto_recap"

    if "jobs" in application.bot_data:
        if "next_recap" in application.bot_data["jobs"]:
            if not application.bot_data["jobs"][autorecap_job_name]["executed"]:
                # eseguo il recap sedutastante
                await create_and_send_recaps(application)
                del application.bot_data["jobs"][autorecap_job_name]

    # programmo i prossimi recap automatici
    time_until_recap = await get_time_until_next_recap()

    await application.job_queue.start()

    job = application.job_queue.run_repeating(
        callback=create_and_send_recaps,
        interval=timedelta(days=7),
        first=time_until_recap,
        name=autorecap_job_name
    )

    bot_logger.info(f"Next autorecap settled at {job.next_t}")

    application.bot_data["jobs"] = {
        # settled to recover the auto recap job in case of forced arrest
        # example format "31_12_9999_23_59_59"
        job.name: {
            "next_date": job.next_t.strftime("%d_%m_%Y_%H_%M_%S"),
            "executed": False
        }
    }

    # setto l'istanza di pyrotgfork
    try:
        pyro_instance = Client(
            name="bridge_bot",
            api_id=os.getenv("API_ID"),
            api_hash=os.getenv("API_HASH"),
            bot_token=os.getenv("BRIDGE_TOKEN")
        )
    except RPCError as e:
        bot_logger.error(e)
        raise

    application.bot_data["pyro_instance"] = pyro_instance

    await pyro_instance.start()

    if "ban_list" not in application.bot_data:
        application.bot_data["ban_list"] = {}


async def get_admins(app: Application):
    """
    :return: l'elenco corrente di admin della chat
    """
    # noinspection PyUnresolvedReferences
    admins = await app.bot.get_chat_administrators(chat_id=app.bot_data["group_chat_id"])
    admins_dict = {}

    for admin in admins:
        user = admin["user"]
        admins_dict[str(user.id)] = user.name

    return admins_dict
