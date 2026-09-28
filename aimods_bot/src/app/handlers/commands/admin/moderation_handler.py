from telegram.ext import PrefixHandler
from aimods_bot.src.callbacks.commands.admin.moderation_router import moderation_command_router

commands_list = [
    "ban",
    "unban",
    "kick",
    "warn",
    "unwarn",
    "limit",
    "unlimit",
    "mute",
    "unmute",
    "delban",
    "delwarn",
    "dellimit",
    "delmute",
    "delkick"
]

moderation_handler = PrefixHandler(
    prefix=[".", "!", "/"],
    command=commands_list,
    callback=moderation_command_router
)
