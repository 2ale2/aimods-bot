from telegram.ext import CallbackQueryHandler, ConversationHandler, PrefixHandler, MessageHandler, filters

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin import admin_main_router
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.handle import set_punishment_duration
from aimods_bot.src.helpers.utils.alerts import open_private_alert
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete_wrapper

alert_handler = CallbackQueryHandler(
    callback=open_private_alert,
    pattern=r"^alert_.+"
)

close_button_handler = CallbackQueryHandler(
    pattern=r"close.*",
    callback=safe_delete_wrapper
)

private_conversation_handler = ConversationHandler(
    entry_points=[
        PrefixHandler([".", "/", "!"], "start", start)
    ],
    states={
        PCS.USER_CONVERSATION: [],  # User main router
        PCS.ADMIN_CONVERSATION: [close_button_handler, CallbackQueryHandler(callback=admin_main_router)],  # Admin main router
        PCS.SET_PUNISHMENT_DURATION: [
            MessageHandler(
                filters=filters.TEXT,
                callback=set_punishment_duration
            ),
            CallbackQueryHandler(callback=admin_main_router)
        ]
    },
    fallbacks=[]
)