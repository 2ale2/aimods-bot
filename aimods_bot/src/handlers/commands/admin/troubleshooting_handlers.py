from telegram.ext import PrefixHandler

from aimods_bot.src.callbacks.commands.admin.troubleshooting import reset_user_conversation, reset_chat_data, \
    erase_callback_queries

reset_user_conversation = PrefixHandler(
    prefix=[".", "/", "!"],
    command="reset_conversation",
    callback=reset_user_conversation
)

reset_user_chat_data = PrefixHandler(
    prefix=[".", "/", "!"],
    command="reset_cdata",
    callback=reset_chat_data
)

erase_callback_queries = PrefixHandler(
    prefix=[".", "/", "!"],
    command="erase_cqueries",
    callback=erase_callback_queries
)
