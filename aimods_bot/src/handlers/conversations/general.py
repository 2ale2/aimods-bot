from telegram.ext import CallbackQueryHandler, ConversationHandler, PrefixHandler

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.helpers.utils.alerts import open_private_alert
# noinspection PyPep8Naming
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


alert_handler = CallbackQueryHandler(
    callback=open_private_alert,
    pattern=r"^alert_.+"
)

private_conversation_handler = ConversationHandler(
    entry_points=[
        PrefixHandler([".", "/", "!"], "start", start)
    ],
    states={
        PCS.USER_CONVERSATION: [],  # User main router
        PCS.ADMIN_CONVERSATION: []  # Admin main router
    },
    fallbacks=[]
)