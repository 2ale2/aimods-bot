import os
from datetime import timedelta, datetime, timezone
from typing import List

from pydantic import ValidationError
from pyrogram import Client
from pyrogram.errors import RPCError
from telegram.ext import Application, BaseHandler

import aimods_bot.src.helpers.constants.constants as constants
from aimods_bot.src.core.config_loader import load_configuration
from aimods_bot.src.core.customcontext import BotData
from aimods_bot.src.core.pydantic import Configuration, JobInfo, CommandConfig
from aimods_bot.src.helpers.constants.constants import (
    SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE, CHANNEL_JOIN_LINK, GROUP_JOIN_LINK
)
from aimods_bot.src.helpers.job_queue import (scheduled_remove_user_request_section_limitation,
                                              scheduled_remove_completed_requests)
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json, set_data_in_json
from aimods_bot.src.helpers.utils.time_utils import get_time_until_next_recap
from aimods_bot.src.tasks.channel_recap import create_and_send_recaps

log = logger.getChild(__name__)


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
        validated_config = Configuration.model_validate(configuration)
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

        text = await get_data_from_json("texts")
        user_joined_message_text = text.get("user_joined_message_text")
        rules_text = text.get("rules_text")
        if (not current_bot_data.user_joined_message_text or
                current_bot_data.user_joined_message_text != user_joined_message_text):
            current_bot_data.user_joined_message_text = user_joined_message_text

        if (not current_bot_data.rules_text or
                current_bot_data.rules_text != rules_text):
            current_bot_data.rules_text = rules_text

        json_commands = await get_data_from_json("commands")
        commands = {}
        for el in json_commands:
            commands[el] = CommandConfig(**json_commands[el])

        if not current_bot_data.commands or current_bot_data.commands != commands:
            current_bot_data.commands = commands

        hashtags = await get_data_from_json("hashtags")
        if not current_bot_data.hashtags or current_bot_data.hashtags != hashtags:
            current_bot_data.hashtags = hashtags

        application.bot_data.base_path = None

        autorecap_job_name = "auto_recap"
        if current_bot_data.jobs:
            j = current_bot_data.jobs.get(autorecap_job_name, None)
            if j and j.next_date and not j.executed and j.next_date <= datetime.now(timezone.utc):
                await create_and_send_recaps(context=application)
                j.executed = True
            del current_bot_data.jobs[autorecap_job_name]

        time_until_next_recap = get_time_until_next_recap()
        await application.job_queue.start()

        job = application.job_queue.run_repeating(
            callback=create_and_send_recaps,
            interval=timedelta(days=7),
            first=time_until_next_recap,
            name=autorecap_job_name
        )

        log.info(f"Next recap settled at {job.next_t}")

        current_bot_data.jobs[autorecap_job_name] = JobInfo(
            next_date=job.next_t,
            executed=False
        )

        new_jobs = {}
        for job_item, j in current_bot_data.jobs.items():
            if not job_item.startswith("remove_inactive_request"):
                new_jobs[job_item] = j
                continue

            if not j or j.executed or not j.next_date:
                continue

            ix = job_item.split(":")[1]
            if j.next_date <= datetime.now(timezone.utc):
                current_bot_data.active_requests.pop(int(ix), None)
                continue

            application.job_queue.run_once(
                callback=scheduled_remove_completed_requests,
                when=j.next_date,
                data={"ix": ix},
                name=job_item,
            )
            new_jobs[job_item] = j

        current_bot_data.jobs = new_jobs

        new_jobs = {}
        now = datetime.now(timezone.utc)
        for job_item, j in current_bot_data.jobs.items():
            if not job_item.startswith("request_limit"):
                new_jobs[job_item] = j
                continue

            if not j or j.executed:
                continue

            _, user_id_str, section = job_item.split(":", 2)
            user_id = int(user_id_str)
            user_data = current_bot_data.user_limitations.get(user_id)
            if not user_data or not user_data.requests:
                continue

            active_limitations = []
            for limitation in user_data.requests:
                # Limitation permanente: tieni ma non rischedulare
                if limitation.until is None:
                    active_limitations.append(limitation)
                    continue

                if limitation.until < now:
                    continue

                log.debug(f"Rescheduling limitation {job_item} ({limitation.until.isoformat()})")
                application.job_queue.run_once(
                    callback=scheduled_remove_user_request_section_limitation,
                    when=limitation.until,
                    data={"user_id": user_id, "section": section},
                    name=job_item,
                )
                new_jobs[job_item] = JobInfo(next_date=limitation.until, executed=False)
                active_limitations.append(limitation)

            user_data.requests = active_limitations

        current_bot_data.jobs = new_jobs

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

        constants.pyro_instance = pyro_inst
        await constants.pyro_instance.start()

        r = await get_data_from_json("restarting")

        if r.get("toggle", False):
            await application.bot.send_message(
                chat_id=r["user_id"],
                text="ℹ️ Bot Riavviato Correttamente"
            )
            await set_data_in_json(key=["restarting", "toggle"], value=False)
            await set_data_in_json(key=["restarting", "user_id"], value=0)

        application.bot_data.configuration.settings.request.cancel_timer = SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE
        application.bot_data.channel_join_link = CHANNEL_JOIN_LINK
        application.bot_data.group_join_link = GROUP_JOIN_LINK


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


async def get_handlers() -> List[BaseHandler]:
    t = await get_data_from_json("test_mode")
    return all_handlers if t else active_handlers
