# raccoglie tutti i dati che servono al funzionamento del bot

import os
import yaml
import constants

from dotenv import load_dotenv
from telegram.ext import Application
from pyrogram import Client
from pyrogram.errors import RPCError

from automatic_tasks import create_and_send_recaps
from loggers import bot_logger
from utils import get_data_from_json, get_time_until_next_recap
from exceptions import handle_validation_errors
from datetime import timedelta


load_dotenv()


def _get_type_map():
    return {
        "str": str,
        "int": int,
        "bool": bool,
        "float": float,
        "dict": dict,
        "list": list
    }


def validate_structure(data, raw_template):
    type_map = _get_type_map()
    template = _deserialize_template(raw_template, type_map)
    return _check_structure(data, template)


def _deserialize_template(template_json, type_map):
    if isinstance(template_json, dict):
        if "type" in template_json:
            t = template_json["type"]
            if isinstance(t, str) and t in type_map:
                template_json["type"] = type_map[t]
        return {k: _deserialize_template(v, type_map) for k, v in template_json.items()}
    return template_json


def _check_structure(data, template, path=""):
    errors = []
    for key, rule in template.items():
        full_path = f"{path}{key}"
        if key not in data:
            errors.append(f"Missing key: {full_path}")
            continue

        value = data[key]

        is_field_definition = isinstance(rule, dict) and "type" in rule and set(rule.keys()) <= {"type", "allowed"}

        if isinstance(rule, dict) and not is_field_definition:
            if not isinstance(value, dict):
                errors.append(f"{full_path} should be a dict")
            else:
                errors.extend(_check_structure(value, rule, full_path + "."))
        else:
            expected_type = rule['type']
            allowed_values = rule.get('allowed')

            if expected_type is int:
                if not (isinstance(value, int) and not isinstance(value, bool)):
                    errors.append(f"{full_path} should be a real integer, got {type(value).__name__}")
            elif not isinstance(value, expected_type):
                errors.append(f"{full_path} should be of type {expected_type.__name__}, got {type(value).__name__}")
            elif allowed_values and value not in allowed_values:
                errors.append(f"{full_path} has invalid value '{value}', allowed: {allowed_values}")
    return errors


async def set_application_data(application: Application):
    """
    Imposta il contenuto di bot_data all'avvio, qualora la persistenza non sia aggiornata.

    Per esempio, se l'elenco admin viene modificato ma, dalla modifica all'arresto del bot, la persistenza non
    si aggiorna (nessun update), l'elenco all'avvio non risulta modificato. Questa funzione sopperisce alla mancanza.
    """

    raw_template = get_data_from_json("configuration_structure")

    try:
        with open("aimods_bot/misc/BotConfigurationStructure.yml", "r") as stream:
            yaml_data = yaml.load(stream, Loader=yaml.FullLoader)
    except Exception as e:
        raise e

    errors = validate_structure(yaml_data, raw_template)
    handle_validation_errors(errors)

    for el in application.user_data:
        if "settings_main_message" in application.user_data[el]:
            del application.user_data[el]["settings_main_message"]

    if "configuration" not in application.bot_data:
        application.bot_data["configuration"] = yaml_data

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
    else:
        application.bot_data["jobs"] = {}

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
        pyro_inst = Client(
            name="bridge_bot",
            api_id=os.getenv("API_ID"),
            api_hash=os.getenv("API_HASH"),
            bot_token=os.getenv("BRIDGE_TOKEN")
        )
    except RPCError as e:
        bot_logger.error(e)
        raise

    _pyro_instance = pyro_inst

    constants.pyro_instance = _pyro_instance

    await constants.pyro_instance.start()

    if "ban_list" not in application.bot_data:
        application.bot_data["ban_list"] = {}


async def post_shutdown(application: Application):
    await constants.pyro_instance.stop()


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
