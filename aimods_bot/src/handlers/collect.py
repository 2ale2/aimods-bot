from aimods_bot.src.handlers.commands.admin.moderation_handler import moderation_handler
from aimods_bot.src.handlers.commands.admin.service_handler import multi_media_echo_handler, service_handler
from aimods_bot.src.handlers.conversations.general import alert_handler, private_conversation_handler, \
    close_button_handler
from aimods_bot.src.handlers.conversations.user.join_handler import new_member_handler

all_handlers = [
    new_member_handler,
    moderation_handler,
    service_handler,
    alert_handler,
    multi_media_echo_handler,
    private_conversation_handler,
    close_button_handler
]
