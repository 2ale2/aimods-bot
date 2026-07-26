import re

from telegram.ext import ConversationHandler, PrefixHandler, CallbackQueryHandler, MessageHandler, filters
from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin import admin_main_router
from aimods_bot.src.callbacks.panels.admin.requests_management.handle import handle_request_rejection_reason
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.route import (
    handle_limitation_user_input,
    handle_limitation_duration, handle_limitation_reason
)
from aimods_bot.src.callbacks.panels.general.router import general_router
from aimods_bot.src.callbacks.panels.general.user_archive.route import handle_user_archive_user_input
from aimods_bot.src.callbacks.panels.user import user_main_router
from aimods_bot.src.callbacks.panels.user.request.handle import handle_wizard_callback_input, handle_wizard_back, \
    handle_wizard_text_input, handle_wizard_confirm
from aimods_bot.src.helpers.constants.constants import COMMAND_PREFIX
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete_wrapper

main_private_conversation_handler = ConversationHandler(
    entry_points=[
        PrefixHandler(
            prefix=COMMAND_PREFIX,
            command="start",
            callback=start
        ),
        CallbackQueryHandler(
            callback=general_router,
            pattern=rf"^(?!(?:{re.escape(GlobalAction.CLOSE_MENU)}|{re.escape(GlobalAction.CLOSE)})$).*$"
        )
    ],
    states={
        PCS.USER_CONVERSATION: [CallbackQueryHandler(callback=user_main_router)],
        PCS.ADMIN_CONVERSATION: [CallbackQueryHandler(callback=admin_main_router)],
        PCS.USER_REQUEST_WIZARD_SESSION: [
            MessageHandler(filters=filters.TEXT, callback=handle_wizard_text_input),
            CallbackQueryHandler(pattern=GlobalAction.REQUEST_WIZARD_BACK, callback=handle_wizard_back),
            CallbackQueryHandler(pattern=GlobalAction.CONFIRM, callback=handle_wizard_confirm),
            CallbackQueryHandler(pattern=GlobalAction.CLOSE, callback=safe_delete_wrapper),
            CallbackQueryHandler(callback=handle_wizard_callback_input)
        ],
        PCS.SET_REQUEST_LIMITATION_USER: [
            MessageHandler(filters=filters.TEXT, callback=handle_limitation_user_input),
            CallbackQueryHandler(callback=admin_main_router)
        ],
        PCS.SET_REQUEST_LIMITATION_DURATION: [
            MessageHandler(filters=filters.TEXT, callback=handle_limitation_duration),
            CallbackQueryHandler(callback=admin_main_router)
        ],
        PCS.SET_REQUEST_LIMITATION_REASON: [
            MessageHandler(filters=filters.TEXT, callback=handle_limitation_reason),
            CallbackQueryHandler(callback=admin_main_router)
        ],
        PCS.SET_USER_FOR_REQUEST_ARCHIVE: [
            MessageHandler(filters=filters.TEXT, callback=handle_user_archive_user_input),
            CallbackQueryHandler(callback=admin_main_router)
        ],
        PCS.SET_REQUEST_REJECTION_REASON: [
            MessageHandler(filters=filters.TEXT, callback=handle_request_rejection_reason),
            CallbackQueryHandler(callback=handle_request_rejection_reason)
        ]
    },
    fallbacks=[
        CallbackQueryHandler(
            callback=safe_delete_wrapper,
            pattern=rf"^(?:{re.escape(GlobalAction.CLOSE_MENU)}|{re.escape(GlobalAction.CLOSE)})$"
        )
    ],
    persistent=True,
    name="main_private_conversation_handler"
)

close_menu_handler = CallbackQueryHandler(callback=safe_delete_wrapper, pattern=GlobalAction.CLOSE_MENU)
