from telegram.ext import PrefixHandler

from aimods_bot.src.callbacks.commands.admin.troubleshooting import reset_user_conversation

reset_user_conversation = PrefixHandler(
    prefix=[".", "/", "!"],
    command="reset_user",
    callback=reset_user_conversation
)
