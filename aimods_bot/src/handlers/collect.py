from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.handlers.commands.admin.moderation_handler import moderation_handler
from aimods_bot.src.handlers.commands.admin.service_handler import multi_media_echo_handler, service_handler, \
    test_command_handler
from aimods_bot.src.handlers.commands.admin.troubleshooting_handlers import reset_user_conversation, \
    reset_user_chat_data, erase_callback_queries, get_chat_data
from aimods_bot.src.handlers.conversations.private_conversation_handlers import (
    alert_handler, private_conversation_handler, close_button_handler, TestHandler
)
from aimods_bot.src.handlers.conversations.join_handler import new_member_handler
from aimods_bot.src.handlers.channel_handlers import channel_posts_capture_handler
from aimods_bot.src.handlers.commands.check_command_handler import check_command_handler


async def test(update: Update, context: CustomContext):
    pass


active_handlers = [
    # TestHandler(callback=test).get(),
    test_command_handler,
    channel_posts_capture_handler,
    new_member_handler,
    private_conversation_handler,
    close_button_handler,
    reset_user_conversation,
    reset_user_chat_data,
    erase_callback_queries,
    get_chat_data
]

all_handlers = [
    # TestHandler(callback=test).get(),
    check_command_handler,
    channel_posts_capture_handler,
    new_member_handler,
    moderation_handler,
    service_handler,
    alert_handler,
    multi_media_echo_handler,
    private_conversation_handler,
    close_button_handler
]
