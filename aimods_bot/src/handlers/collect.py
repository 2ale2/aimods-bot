from aimods_bot.src.handlers.conversations.user.join_handler import new_member_handler
from aimods_bot.src.handlers.commands.admin.moderation_handler import moderation_handler
from aimods_bot.src.handlers.conversations.general import alert_handler

all_handlers = [
    new_member_handler,
    moderation_handler,
    alert_handler
]
