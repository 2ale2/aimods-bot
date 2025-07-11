import os
import aimods_bot.src.helpers.constants as constants
from datetime import timedelta
from telegram.ext import Application
from pyrogram import Client
from pyrogram.errors import RPCError
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json
from aimods_bot.src.helpers.utils.time_utils import get_time_until_next_recap
from aimods_bot.src.tasks.channel_recap import create_and_send_recaps
from aimods_bot.src.core.config_loader import load_configuration

log = logger.getChild("application_setup")


async def set_application_data(application: Application):
    """
    Sets up the application data, including configuration, admins, texts, and jobs.

    Args:
        application (Application): The Telegram application instance.
    """

    # Load configuration
    if "configuration" not in application.bot_data:
        application.bot_data["configuration"] = load_configuration()

    # Set group chat ID
    group_chat_id = os.getenv("GROUP_CHAT_ID")
    if ('group_chat_id' not in application.bot_data or
            application.bot_data["group_chat_id"] != group_chat_id or
            application.bot_data["group_chat_id"] is None):
        application.bot_data["group_chat_id"] = group_chat_id

    # Set admins
    admins = await get_admins(application)
    if 'admins' not in application.bot_data or application.bot_data["admins"] != admins:
        application.bot_data["admins"] = admins

    # Set texts
    texts = get_data_from_json("texts")
    user_joined_message_text = texts["user_joined_message_text"]
    if ('user_joined_message_text' not in application.bot_data or
            application.bot_data["user_joined_message_text"] != user_joined_message_text):
        application.bot_data["user_joined_message_text"] = user_joined_message_text

    rules_text = texts["rules_text"]
    if 'rules_text' not in application.bot_data or application.bot_data["rules_text"] != rules_text:
        application.bot_data["rules_text"] = rules_text

    # Set commands
    commands = get_data_from_json("commands")
    if 'commands' not in application.bot_data or application.bot_data["commands"] != commands:
        application.bot_data["commands"] = commands

    # Set hashtags
    hashtags = get_data_from_json("hashtags")
    if 'hashtags' not in application.bot_data or application.bot_data["hashtags"] != hashtags:
        application.bot_data["hashtags"] = hashtags

    # Clear outdated settings
    for el in application.user_data:
        if "settings_main_message" in application.user_data[el]:
            del application.user_data[el]["settings_main_message"]

    # Set up autorecap job
    autorecap_job_name = "auto_recap"
    if "jobs" in application.bot_data:
        if "next_recap" in application.bot_data["jobs"]:
            if not application.bot_data["jobs"][autorecap_job_name]["executed"]:
                await create_and_send_recaps(application)
                del application.bot_data["jobs"][autorecap_job_name]
    else:
        application.bot_data["jobs"] = {}

    time_until_recap = await get_time_until_next_recap()
    await application.job_queue.start()

    job = application.job_queue.run_repeating(
        callback=create_and_send_recaps,
        interval=timedelta(days=7),
        first=time_until_recap,
        name=autorecap_job_name
    )

    log.info(f"Next autorecap settled at {job.next_t}")

    application.bot_data["jobs"] = {
        job.name: {
            "next_date": job.next_t.strftime("%d_%m_%Y_%H_%M_%S"),
            "executed": False
        }
    }

    # Set up Pyrogram instance
    try:
        pyro_inst = Client(
            name="bridge_bot",
            api_id=os.getenv("API_ID"),
            api_hash=os.getenv("API_HASH"),
            bot_token=os.getenv("BRIDGE_TOKEN")
        )
    except RPCError as e:
        log.error(f"Failed to initialize Pyrogram client: {e}")
        raise

    constants.pyro_instance = pyro_inst
    await constants.pyro_instance.start()

    # Initialize ban list
    if "ban_list" not in application.bot_data:
        application.bot_data["ban_list"] = {}


async def get_admins(app: Application):
    """
    Retrieves the list of administrators for the group chat.

    Args:
        app (Application): The Telegram application instance.

    Returns:
        dict: A dictionary mapping admin IDs to their names.
    """
    admins = await app.bot.get_chat_administrators(chat_id=app.bot_data["group_chat_id"])
    admins_dict = {}

    for admin in admins:
        user = admin["user"]
        admins_dict[str(user.id)] = user.name

    return admins_dict
