from aimods_bot.src.handlers.commands.admin.moderation_handler import moderation_handler
from aimods_bot.src.handlers.commands.admin.service_handler import multi_media_echo_handler, service_handler, \
    test_command_handler
from aimods_bot.src.handlers.conversations.private_conversation_handlers import alert_handler, private_conversation_handler, \
    close_button_handler, TestHandler
from aimods_bot.src.handlers.conversations.join_handler import new_member_handler
from aimods_bot.src.handlers.channel_handlers import channel_posts_capture_handler
from aimods_bot.src.helpers.utils.telegram_utils import test

active_handlers = [
    TestHandler(callback=test).get(),
    test_command_handler,
    channel_posts_capture_handler,
    new_member_handler
]

all_handlers = [
    # TestHandler(callback=test).get(),
    channel_posts_capture_handler,
    new_member_handler,
    moderation_handler,
    service_handler,
    alert_handler,
    multi_media_echo_handler,
    private_conversation_handler,
    close_button_handler
]
