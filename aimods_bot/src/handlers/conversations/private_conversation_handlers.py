from telegram import Update
from telegram.ext import CallbackQueryHandler, ConversationHandler, PrefixHandler, MessageHandler, filters, TypeHandler

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin import admin_main_router
from aimods_bot.src.callbacks.panels.user import user_main_router
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.handle import handle_user_input as handler_user_input_links
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.handle import \
    handle_user_input_antispam_whitelist
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.route import antispam_whitelist_backer
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.handle import set_punishment_duration
from aimods_bot.src.callbacks.panels.user.request_management.request.android_request import request_app_name, \
    request_app_link, request_app_version, request_app_functionalities, recheck_request, edit_request_detail, \
    edited_detail, confirm_request, backer
from aimods_bot.src.helpers.constants.conversation_states import \
    PrivateConversationState as PCS, AndroidRequestConversationState as ARCS
from aimods_bot.src.helpers.filters import ChatSharedFilter
from aimods_bot.src.helpers.utils.alerts import open_private_alert
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete_wrapper, test


chat_shared_filter = ChatSharedFilter()


alert_handler = CallbackQueryHandler(
    callback=open_private_alert,
    pattern=r"^alert_.+"
)


class TestHandler:
    def __init__(self, callback):
        self.callback = callback

    def get(self):
        return TypeHandler(
            type=Update,
            callback=self.callback
        )


close_button_handler = CallbackQueryHandler(
    pattern=r"(^|.*)close_menu$",
    callback=safe_delete_wrapper
)


android_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            pattern="user/manage_requests/add_request/android",
            callback=request_app_name
        )
    ],
    states={
        ARCS.APP_NAME: [MessageHandler(filters=filters.TEXT, callback=request_app_link)],
        ARCS.APP_LINK: [MessageHandler(filters=filters.Entity("url"), callback=request_app_version)],
        ARCS.APP_VERSION: [MessageHandler(filters=filters.TEXT, callback=request_app_functionalities)],
        ARCS.APP_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=recheck_request)],
        ARCS.CHECK_REQUEST: [
            CallbackQueryHandler(
                pattern="confirm_request",
                callback=confirm_request
            ),
            CallbackQueryHandler(
                pattern="^edit_.+$",
                callback=edit_request_detail
            )
        ],
        ARCS.EDIT_NAME: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
        ARCS.EDIT_LINK: [MessageHandler(filters=filters.Entity("url"), callback=edited_detail)],
        ARCS.EDIT_VERSION: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
        ARCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
    },
    fallbacks=[CallbackQueryHandler(pattern="^back_.+$", callback=backer)],
    map_to_parent={
        ARCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    }
)


private_conversation_handler = ConversationHandler(
    entry_points=[
        PrefixHandler([".", "/", "!"], "start", start)
    ],
    states={
        PCS.USER_CONVERSATION: [close_button_handler, CallbackQueryHandler(callback=user_main_router)],  # User main router
        PCS.ADMIN_CONVERSATION: [close_button_handler, CallbackQueryHandler(callback=admin_main_router)],  # Admin main router
        PCS.SET_PUNISHMENT_DURATION: [
            MessageHandler(
                filters=filters.TEXT,
                callback=set_punishment_duration
            ),
            CallbackQueryHandler(callback=admin_main_router)
        ],
        PCS.EDIT_ANTISPAM_LINK_LIST: [
            # TestHandler(callback=test),
            MessageHandler(
                filters=filters.TEXT,
                callback=handler_user_input_links
            ),
            close_button_handler,
            CallbackQueryHandler(callback=admin_main_router)
        ],
        PCS.ADD_ANTISPAM_MENTION_WHITELIST: [
            MessageHandler(
                filters=filters.Text(["🔙 Indietro", "indietro", "Indietro"]),
                callback=antispam_whitelist_backer
            ),
            MessageHandler(
                filters=chat_shared_filter,
                callback=handle_user_input_antispam_whitelist
            )
        ],
        PCS.REMOVE_ANTISPAM_MENTION_WHITELIST: [
            MessageHandler(
                filters=filters.TEXT,
                callback=handle_user_input_antispam_whitelist
            ),
            CallbackQueryHandler(callback=admin_main_router)
        ],
        PCS.NEW_REQUEST: [android_request_handler]
    },
    fallbacks=[CallbackQueryHandler(callback=user_main_router)],
    allow_reentry=True
)