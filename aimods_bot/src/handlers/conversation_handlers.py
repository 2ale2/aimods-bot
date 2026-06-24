from telegram.ext import ConversationHandler, PrefixHandler, CallbackQueryHandler, MessageHandler, filters
from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin import admin_main_router
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.route import handle_limitation_user_input
from aimods_bot.src.callbacks.panels.user import user_main_router
from aimods_bot.src.callbacks.panels.user.request.handle import handle_wizard_callback_input, handle_wizard_back, \
    handle_wizard_text_input
from aimods_bot.src.helpers.constants.constants import COMMAND_PREFIX
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction

main_private_conversation_handler = ConversationHandler(
    entry_points=[
        PrefixHandler(
            prefix=COMMAND_PREFIX,
            command="start",
            callback=start
        )
    ],
    states={
        PCS.USER_CONVERSATION: [CallbackQueryHandler(callback=user_main_router)],
        PCS.ADMIN_CONVERSATION: [CallbackQueryHandler(callback=admin_main_router)],
        PCS.USER_REQUEST_WIZARD_SESSION: [
            MessageHandler(filters=filters.TEXT, callback=handle_wizard_text_input),
            CallbackQueryHandler(pattern=GlobalAction.REQUEST_WIZARD_BACK, callback=handle_wizard_back),
            CallbackQueryHandler(callback=handle_wizard_callback_input)
        ],
        PCS.SET_REQUEST_LIMITATION_USER: [
            MessageHandler(filters=filters.TEXT, callback=handle_limitation_user_input),
            CallbackQueryHandler(callback=admin_main_router)
        ]
    },
    fallbacks=[]
)
