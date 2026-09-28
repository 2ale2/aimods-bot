from telegram.ext import PrefixHandler

from aimods_bot.src.features.service.check import check_status


check_command_handler = PrefixHandler(
    prefix=["/", ".", "!"],
    command="check",
    callback=check_status
)
