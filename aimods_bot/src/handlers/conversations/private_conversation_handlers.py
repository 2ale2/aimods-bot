from telegram import Update
from telegram.ext import CallbackQueryHandler, ConversationHandler, PrefixHandler, MessageHandler, filters, TypeHandler

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin import admin_main_router
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.handle import \
    handle_user_input as handler_user_input_links
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.handle import \
    handle_user_input_antispam_whitelist
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.route import antispam_whitelist_backer
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.handle import set_punishment_duration
from aimods_bot.src.callbacks.panels.admin.requests_management.handle import \
    handle_request_rejection_reason, handle_user_archive_identifier
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import \
    render_handled_request_limitation_duration_panel, render_admin_user_limitation_confirmed_panel, \
    handle_limitation_identifier
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.route import route_admin_limit_user_request
from aimods_bot.src.callbacks.panels.user import user_main_router
from aimods_bot.src.handlers.request_handlers import android_request_handler, windows_request_handler, \
    ios_request_handler, macos_request_handler, windows_game_request_handler, windows_adobe_request_handler, \
    windows_software_request_handler, windows_daw_request_handler, macos_daw_request_handler, \
    macos_software_request_handler
from aimods_bot.src.helpers.constants.conversation_states import \
    PrivateConversationState as PCS
from aimods_bot.src.helpers.filters import ChatSharedFilter
from aimods_bot.src.helpers.utils.alerts import open_private_alert
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete_wrapper

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
    pattern=r"^.*close_menu.*$",
    callback=safe_delete_wrapper
)

private_conversation_handler = ConversationHandler(
    entry_points=[
        PrefixHandler(
            prefix=[".", "/", "!"],
            command="start",
            callback=start,
            filters=filters.ChatType.PRIVATE
        )
    ],
    states={
        # User main router
        PCS.USER_CONVERSATION: [
            android_request_handler,
            windows_game_request_handler,
            windows_adobe_request_handler,
            windows_software_request_handler,
            windows_daw_request_handler,
            ios_request_handler,
            macos_daw_request_handler,
            macos_software_request_handler,
            CallbackQueryHandler(
                pattern=r"^(?!.*close_menu)(?!(?=.*add_request)(?=.*from_notification)).*$",
                callback=user_main_router
            ),
            close_button_handler
        ],
        # Admin main router
        PCS.ADMIN_CONVERSATION: [
            CallbackQueryHandler(pattern=r"^(?!.*close_menu).*$", callback=admin_main_router),
            close_button_handler
        ],
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
            CallbackQueryHandler(pattern=r"^(?!.*close_menu).*$", callback=admin_main_router)
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
        PCS.NEW_REQUEST: [android_request_handler, windows_request_handler, ios_request_handler, macos_request_handler],
        PCS.SET_REQUEST_LIMITATION_DURATION: [
            MessageHandler(
                filters=filters.TEXT,
                callback=render_handled_request_limitation_duration_panel
            ),
            CallbackQueryHandler(pattern=r"^(?!.*close_menu).*$", callback=admin_main_router),
            close_button_handler
        ],
        PCS.SET_REQUEST_LIMITATION_REASON: [
            MessageHandler(
                filters=filters.TEXT,
                callback=render_admin_user_limitation_confirmed_panel
            ),
            CallbackQueryHandler(callback=admin_main_router)
        ],
        PCS.SET_REQUEST_LIMITATION_USER: [
            MessageHandler(
                filters=filters.TEXT,
                callback=route_admin_limit_user_request
            ),
            close_button_handler,
            CallbackQueryHandler(pattern=r"^(?!.*close_menu).*$", callback=admin_main_router)
        ],
        PCS.SET_REQUEST_REJECTION_REASON: [
            MessageHandler(
                filters=filters.TEXT,
                callback=handle_request_rejection_reason
            ),
            close_button_handler,
            CallbackQueryHandler(pattern=r"^(?!.*close_menu).*$", callback=admin_main_router)
        ],
        PCS.SET_VIEW_REQUEST_LIMITATION_USER: [
            MessageHandler(
                filters=filters.TEXT,
                callback=handle_limitation_identifier
            ),
            close_button_handler,
            CallbackQueryHandler(pattern=r"^(?!.*close_menu).*$", callback=admin_main_router)
        ],
        PCS.SET_USER_FOR_REQUEST_ARCHIVE: [
            MessageHandler(
                filters=filters.TEXT,
                callback=handle_user_archive_identifier
            ),
            close_button_handler,
            CallbackQueryHandler(pattern=r"^(?!.*close_menu).*$", callback=admin_main_router)
        ]
    },
    fallbacks=[CallbackQueryHandler(callback=user_main_router)],
    allow_reentry=True,
    name="private_conversation",
    persistent=True
)
