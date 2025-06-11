from aimods_bot.modules import handlers_function
from telegram.ext import MessageHandler, filters

commands_handler = MessageHandler(
            filters=(filters.TEXT | filters.CAPTION)
            & (filters.Regex(r"^[/.!]") | filters.CaptionRegex(r"^[/.!]")),
            callback=handlers_function.handle_command)