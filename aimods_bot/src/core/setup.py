import os
from typing import List

from pydantic import ValidationError

import aimods_bot.src.helpers.constants.constants as constants
from datetime import timedelta, datetime
from telegram.ext import Application, BaseHandler
from pyrogram import Client
from pyrogram.errors import RPCError

from aimods_bot.src.core.pydantic import Configuration, JobInfo, RequestConversationFlow, CommandConfig
from aimods_bot.src.core.customcontext import BotData
from aimods_bot.src.helpers.constants.constants import SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json, set_data_in_json
from aimods_bot.src.helpers.utils.time_utils import get_time_until_next_recap
from aimods_bot.src.tasks.channel_recap import create_and_send_recaps
from aimods_bot.src.core.config_loader import load_configuration
from aimods_bot.src.handlers.collect import all_handlers, active_handlers

log = logger.getChild("application_setup")


# noinspection PyUnresolvedReferences
async def set_application_data(application: Application):
    try:
        if isinstance(application.bot_data, BotData):
            current_bot_data = application.bot_data
        else:
            current_bot_data = BotData.model_validate(application.bot_data)
    except ValidationError as e:
        log.error(f"Errori di struttura in Bot Data: {e}\n\nInizializzo.")
        current_bot_data = BotData()

    configuration = load_configuration()
    try:
        validated_config = Configuration(**configuration)
        current_bot_data.configuration = validated_config
    except ValidationError as e:
        log.error(f"Invalid configuration: {e}. I will use the old one.")
    else:
        group_chat_id = int(os.getenv("GROUP_CHAT_ID"))
        if not current_bot_data.group_chat_id or current_bot_data.group_chat_id != group_chat_id:
            current_bot_data.group_chat_id = group_chat_id

        admins = await get_admins(app=application, chat_id=current_bot_data.group_chat_id)
        if not current_bot_data.admins or current_bot_data.admins != admins:
            current_bot_data.admins = admins

        text = get_data_from_json("texts")
        user_joined_message_text = text.get("user_joined_message_text")
        rules_text = text.get("rules_text")
        if (not current_bot_data.user_joined_message_text or
            current_bot_data.user_joined_message_text != user_joined_message_text):
            current_bot_data.user_joined_message_text = user_joined_message_text

        if (not current_bot_data.rules_text or
            current_bot_data.rules_text != rules_text):
            current_bot_data.rules_text = rules_text

        json_commands = get_data_from_json("commands")
        commands = {}
        for el in json_commands:
            commands[el] = CommandConfig(**json_commands[el])

        if not current_bot_data.commands or current_bot_data.commands != commands:
            current_bot_data.commands = commands

        hashtags = get_data_from_json("hashtags")
        if not current_bot_data.hashtags or current_bot_data.hashtags != hashtags:
            current_bot_data.hashtags = hashtags

        json_request_conversation_flows = get_data_from_json("request_conversation_flows")
        request_conversation_flows = {}
        for pl in json_request_conversation_flows:
            request_conversation_flows[pl] = {}
            for ct in json_request_conversation_flows[pl]:
                request_conversation_flows[pl][ct] = RequestConversationFlow(
                    **json_request_conversation_flows[pl][ct]
                )

        for uid in application.user_data:
            if "settings_main_message" in application.user_data[uid]:
                del application.user_data[uid]["settings_main_message"]

        for el in application.chat_data:
            if "setting_duration" in application.chat_data[el]:
                del application.chat_data[el]["setting_duration"]
            if "update_message" in application.chat_data[el]:
                del application.chat_data[el]["update_message"]

        autorecap_job_name = "auto_recap"
        if current_bot_data.jobs:
            j = current_bot_data.jobs.get(autorecap_job_name, None)
            if j and not j.executed:
                execution_time = datetime.strptime(j.next_date, "%d_%m_%Y_%H_%M_%S")
                if execution_time <= datetime.now():
                    await create_and_send_recaps(context=application)
                del current_bot_data.jobs[autorecap_job_name]

        time_until_next_recap = await get_time_until_next_recap()
        await application.job_queue.start()

        job = application.job_queue.run_repeating(
            callback=create_and_send_recaps,
            interval=timedelta(days=7),
            first=time_until_next_recap,
            name=autorecap_job_name
        )

        log.info(f"Next recap settled at {job.next_t}")

        current_bot_data.jobs[autorecap_job_name] = JobInfo(
            next_date=job.next_t.strftime("%d_%m_%Y_%H_%M_%S"),
            executed=False
        )

        try:
            pyro_inst = Client(
                name="bridge_bot",
                api_id=os.getenv("API_ID"),
                api_hash=os.getenv("API_HASH"),
                bot_token=os.getenv("BOT_TOKEN")
            )
        except RPCError as e:
            log.error(f"Failed to initialize Pyrogram client: {e}")
            raise

        _pyro_instance = pyro_inst
        constants.pyro_instance = _pyro_instance
        await constants.pyro_instance.start()

        r = get_data_from_json("restarting")

        if r.get("toggle", False):
            await application.bot.send_message(
                chat_id=r["user_id"],
                text="ℹ️ Bot Riavviato Correttamente"
            )
            set_data_in_json(key=["restarting", "toggle"], value=False)
            set_data_in_json(key=["restarting", "user_id"], value=0)

        application.bot_data.configuration.settings.request.cancel_timer = SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE


# noinspection PyUnresolvedReferences
async def get_admins(app: Application, chat_id: int):
    """
    Retrieves the list of administrators for the group chat.

    Args:
        app (Application): The Telegram application instance.
        chat_id (int): The id of the chat.

    Returns:
        dict: A dictionary mapping admin IDs to their names.
    """
    admins = await app.bot.get_chat_administrators(chat_id=chat_id)
    admins_dict = {}

    for admin in admins:
        user = admin["user"]
        admins_dict[str(user.id)] = user.name

    return admins_dict


def get_handlers() -> List[BaseHandler]:
    t = get_data_from_json("test_mode")
    return all_handlers if not t else active_handlers
