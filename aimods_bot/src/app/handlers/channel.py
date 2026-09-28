import os

from telegram.ext import MessageHandler, filters
from aimods_bot.src.tasks.channel_recap import catch_post_from_channel

CHANNEL_ID = int(os.environ["CHANNEL_ID"])

channel_post_capture_handler = MessageHandler(
    filters=filters.UpdateType.CHANNEL_POST & (filters.TEXT | filters.CAPTION) & filters.Chat(chat_id=CHANNEL_ID),
    callback=catch_post_from_channel
)
