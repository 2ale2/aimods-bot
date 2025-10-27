from telegram.ext import PrefixHandler

from aimods_bot.src.callbacks.commands.admin.troubleshooting import reset_user_data

reset_user_data = PrefixHandler(
    prefix=[".", "/", "!"],
    command="reset_user",
    callback=reset_user_data
)
