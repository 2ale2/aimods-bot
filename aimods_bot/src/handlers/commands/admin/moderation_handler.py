from telegram.ext import PrefixHandler
from aimods_bot.src.callbacks.commands.admin.moderation_router import moderation_command_router


moderation_handler = PrefixHandler(
    [".", "!", "/"],
    ["ban", "unban", "kick", "warn", "unwarn"],
    moderation_command_router
)
