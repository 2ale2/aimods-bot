from telegram.ext import PrefixHandler, MessageHandler
from aimods_bot.src.helpers.filters import MediaGroupIDMessageFilter
from aimods_bot.src.callbacks.commands.admin.service_router import service_command_router, handle_media_group

# Tutti i messaggi a eccezione di quelli che possiedono più di un allegato
service_handler = PrefixHandler(
    [".", "!", "/"],
    ["annuncio", "echo"],
    service_command_router
)


# Messaggi contenenti più di un allegato
media_group_id_message_filer = MediaGroupIDMessageFilter()

multi_media_echo_handler = MessageHandler(
    filters=media_group_id_message_filer,
    callback=handle_media_group
)


