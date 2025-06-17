from aimods_bot.modules import handlers_function
from telegram.ext import MessageHandler, filters
from aimods_bot.modules.globals import ChannelMessageForRecapFilter

channel_message_for_recap_filter = ChannelMessageForRecapFilter()

channel_posts_capture_handler = MessageHandler(
            filters=filters.Chat(chat_id=-1002544860500) & channel_message_for_recap_filter,
            callback=handlers_function.catch_post_from_channel
        )