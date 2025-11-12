import os
import asyncio

from telegram.ext import MessageHandler, filters, PrefixHandler

from aimods_bot.src.callbacks.commands.admin.test_mode import test_mode_command
from aimods_bot.src.helpers.filters import MediaGroupIDMessageFilter
from aimods_bot.src.callbacks.commands.admin.service_router import service_command_router
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json


echo_pattern = asyncio.run(get_data_from_json("commands"))["echo"]["pattern"]


# Tutti i messaggi a eccezione di quelli che possiedono più di un allegato
service_handler = MessageHandler(
    filters=filters.CaptionRegex(pattern=echo_pattern) | filters.Regex(pattern=echo_pattern),
    callback=service_command_router
)

# Messaggi contenenti più di un allegato
media_group_id_message_filer = MediaGroupIDMessageFilter()

multi_media_echo_handler = MessageHandler(
    filters=media_group_id_message_filer,
    callback=service_command_router
)

test_command_handler = PrefixHandler(
    prefix=[".", "!", "/"],
    command="test",
    callback=test_mode_command,
    filters=filters.User(int(os.getenv("MYID"))) & filters.ChatType.PRIVATE
)
