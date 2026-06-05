from telegram.ext import ConversationHandler, PrefixHandler

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin import admin_main_router
from aimods_bot.src.callbacks.panels.user import user_main_router
from aimods_bot.src.helpers.constants.constants import COMMAND_PREFIX
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS

main_private_conversation_handler = ConversationHandler(
    entry_points=[
        PrefixHandler(
            prefix=COMMAND_PREFIX,
            command="start",
            callback=start
        )
    ],
    states={
        PCS.USER_CONVERSATION: [user_main_router],
        PCS.ADMIN_CONVERSATION: [admin_main_router],
        # TODO: PCS.USER_REQUEST_WIZARD_SESSION: [funzione di hanlding]
    },
    fallbacks=[]
)