from telegram.ext import PrefixHandler

from aimods_bot.src.callbacks.commands.general.check_command import check_status


check_command_handler = PrefixHandler(
    prefix=["/", ".", "!"],
    command="check",
    callback=check_status
)
