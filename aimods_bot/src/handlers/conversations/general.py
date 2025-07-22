from telegram.ext import CallbackQueryHandler, ConversationHandler, PrefixHandler

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.helpers.utils.alerts import open_private_alert
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as pcs


alert_handler = CallbackQueryHandler(
    callback=open_private_alert,
    pattern=r"^alert_.+"
)

private_conversation_handler = ConversationHandler(
    entry_points=[
        PrefixHandler([".", "/", "!"], "start", start)
    ],
    states={
        pcs.USER_CONVERSATION: [],  # User main router
        pcs.ADMIN_CONVERSATION: []  # Admin main router
    },
    fallbacks=[]
)