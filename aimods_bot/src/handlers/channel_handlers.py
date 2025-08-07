import os
from telegram.ext import MessageHandler, filters

from aimods_bot.src.helpers.filters import ChannelMessageForRecapFilter
from aimods_bot.src.tasks.channel_recap import catch_post_from_channel

channel_message_for_recap_filter = ChannelMessageForRecapFilter()

channel_posts_capture_handler = MessageHandler(
            filters=filters.Chat(chat_id=int(os.getenv("CHANNEL_ID"))) & channel_message_for_recap_filter,
            callback=catch_post_from_channel
        )
