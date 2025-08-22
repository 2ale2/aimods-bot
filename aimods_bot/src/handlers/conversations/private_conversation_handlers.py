from telegram import Update
from telegram.ext import CallbackQueryHandler, ConversationHandler, PrefixHandler, MessageHandler, filters, TypeHandler

from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin import admin_main_router
from aimods_bot.src.callbacks.panels.user import user_main_router
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.handle import \
    handle_user_input as handler_user_input_links
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.handle import \
    handle_user_input_antispam_whitelist
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.route import antispam_whitelist_backer
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.handle import set_punishment_duration
from aimods_bot.src.callbacks.panels.user.request_management.request import request_detail, recheck_request, \
    confirm_request, edit_request_detail, edited_detail, backer
from aimods_bot.src.callbacks.panels.user.request_management.route import request_category, request_router
from aimods_bot.src.helpers.constants.conversation_states import \
    PrivateConversationState as PCS, RequestConversationState as RCS
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
            callback=request_category
        )
    ],
    states={
        RCS.REQUEST_NAME: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
        RCS.REQUEST_LINK: [MessageHandler(filters=filters.Entity("url"), callback=request_detail)],
        RCS.REQUEST_VERSION: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
        RCS.REQUEST_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=recheck_request)],
        RCS.CHECK_REQUEST: [
            CallbackQueryHandler(
                pattern="confirm_request",
                callback=confirm_request
            ),
            CallbackQueryHandler(
                pattern="^edit_.+$",
                callback=edit_request_detail
            )
        ],
        RCS.EDIT_NAME: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
        RCS.EDIT_LINK: [MessageHandler(filters=filters.Entity("url"), callback=edited_detail)],
        RCS.EDIT_VERSION: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
        RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
    },
    fallbacks=[CallbackQueryHandler(pattern="^back_.+$", callback=backer)],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    }
)


windows_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            pattern="user/manage_requests/add_request/windows",
            callback=request_category
        )
    ],
    states={
        RCS.REQUEST_CATEGORY: [
            ConversationHandler(
                entry_points=[CallbackQueryHandler(pattern="game", callback=request_router)],
                states={
                    RCS.REQUEST_NAME: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
                    RCS.REQUEST_LINK: [MessageHandler(filters=filters.Entity("url"), callback=request_detail)],
                    RCS.REQUEST_VERSION: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
                    RCS.REQUEST_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
                    RCS.REQUEST_STEAMTOOLS: [CallbackQueryHandler(pattern="^steamtools_.+", callback=recheck_request)],
                    RCS.CHECK_REQUEST: [
                        CallbackQueryHandler(
                            pattern="confirm_request",
                            callback=confirm_request
                        ),
                        CallbackQueryHandler(
                            pattern="^(?:edit_|steamtools_).+",
                            callback=edit_request_detail
                        ),
                    ],
                    RCS.EDIT_NAME: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_LINK: [MessageHandler(filters=filters.Entity("url"), callback=edited_detail)],
                    RCS.EDIT_VERSION: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)]
                },
                fallbacks=[CallbackQueryHandler(pattern="^back_.+$", callback=backer)],
                map_to_parent={
                    ConversationHandler.END: ConversationHandler.END,
                    RCS.MAIN_BACKER: RCS.MAIN_BACKER
                }
            ),
            ConversationHandler(
                entry_points=[CallbackQueryHandler(pattern="adobe", callback=request_router)],
                states={
                    RCS.REQUEST_NAME: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
                    RCS.REQUEST_VERSION: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
                    RCS.REQUEST_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=recheck_request)],
                    RCS.CHECK_REQUEST: [
                        CallbackQueryHandler(
                            pattern="confirm_request",
                            callback=confirm_request
                        ),
                        CallbackQueryHandler(
                            pattern="^edit_.+$",
                            callback=edit_request_detail
                        )
                    ],
                    RCS.EDIT_NAME: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_LINK: [MessageHandler(filters=filters.Entity("url"), callback=edited_detail)],
                    RCS.EDIT_VERSION: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)]
                },
                fallbacks=[CallbackQueryHandler(pattern="^back_.+$", callback=backer)],
                map_to_parent={
                    ConversationHandler.END: ConversationHandler.END,
                    RCS.MAIN_BACKER: RCS.MAIN_BACKER
                }
            ),
            ConversationHandler(
                entry_points=[CallbackQueryHandler(pattern="daw", callback=request_router)],
                states={
                    RCS.REQUEST_NAME: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
                    RCS.REQUEST_LINK: [MessageHandler(filters=filters.Entity("url"), callback=request_detail)],
                    RCS.REQUEST_VERSION: [MessageHandler(filters=filters.TEXT, callback=recheck_request)],
                    RCS.CHECK_REQUEST: [
                        CallbackQueryHandler(
                            pattern="confirm_request",
                            callback=confirm_request
                        ),
                        CallbackQueryHandler(
                            pattern="^edit_.+$",
                            callback=edit_request_detail
                        )
                    ],
                    RCS.EDIT_NAME: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_LINK: [MessageHandler(filters=filters.Entity("url"), callback=edited_detail)],
                    RCS.EDIT_VERSION: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)]
                },
                fallbacks=[CallbackQueryHandler(pattern="^back_.+$", callback=backer)],
                map_to_parent={
                    ConversationHandler.END: ConversationHandler.END,
                    RCS.MAIN_BACKER: RCS.MAIN_BACKER
                }
            ),
            ConversationHandler(
                entry_points=[CallbackQueryHandler(pattern="software", callback=request_router)],
                states={
                    RCS.REQUEST_NAME: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
                    RCS.REQUEST_LINK: [MessageHandler(filters=filters.Entity("url"), callback=request_detail)],
                    RCS.REQUEST_VERSION: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
                    RCS.REQUEST_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=recheck_request)],
                    RCS.CHECK_REQUEST: [
                        CallbackQueryHandler(
                            pattern="confirm_request",
                            callback=confirm_request
                        ),
                        CallbackQueryHandler(
                            pattern="^edit_.+$",
                            callback=edit_request_detail
                        )
                    ],
                    RCS.EDIT_NAME: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_LINK: [MessageHandler(filters=filters.Entity("url"), callback=edited_detail)],
                    RCS.EDIT_VERSION: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)]
                },
                fallbacks=[CallbackQueryHandler(pattern="^back_.+$", callback=backer)],
                map_to_parent={
                    ConversationHandler.END: ConversationHandler.END,
                    RCS.MAIN_BACKER: RCS.MAIN_BACKER
                }
            )
        ],
    },
    fallbacks=[CallbackQueryHandler(pattern="^back_.+$", callback=backer)],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    }
)

ios_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            pattern="user/manage_requests/add_request/ios",
            callback=request_category
        )
    ],
    states={
        RCS.REQUEST_NAME: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
        RCS.REQUEST_LINK: [MessageHandler(filters=filters.Entity("url"), callback=request_detail)],
        RCS.REQUEST_VERSION: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
        RCS.REQUEST_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=recheck_request)],
        RCS.CHECK_REQUEST: [
            CallbackQueryHandler(
                pattern="confirm_request",
                callback=confirm_request
            ),
            CallbackQueryHandler(
                pattern="^edit_.+$",
                callback=edit_request_detail
            )
        ],
        RCS.EDIT_NAME: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
        RCS.EDIT_LINK: [MessageHandler(filters=filters.Entity("url"), callback=edited_detail)],
        RCS.EDIT_VERSION: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
        RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
    },
    fallbacks=[CallbackQueryHandler(pattern="^back_.+$", callback=backer)],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    }
)

macos_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            pattern="user/manage_requests/add_request/macos",
            callback=request_category
        )
    ],
    states={
        RCS.REQUEST_CATEGORY: [
            ConversationHandler(
                entry_points=[CallbackQueryHandler(pattern="daw", callback=request_router)],
                states={
                    RCS.REQUEST_NAME: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
                    RCS.REQUEST_LINK: [MessageHandler(filters=filters.Entity("url"), callback=request_detail)],
                    RCS.REQUEST_VERSION: [MessageHandler(filters=filters.TEXT, callback=recheck_request)],
                    RCS.CHECK_REQUEST: [
                        CallbackQueryHandler(
                            pattern="confirm_request",
                            callback=confirm_request
                        ),
                        CallbackQueryHandler(
                            pattern="^edit_.+$",
                            callback=edit_request_detail
                        )
                    ],
                    RCS.EDIT_NAME: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_LINK: [MessageHandler(filters=filters.Entity("url"), callback=edited_detail)],
                    RCS.EDIT_VERSION: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)]
                },
                fallbacks=[CallbackQueryHandler(pattern="^back_.+$", callback=backer)],
                map_to_parent={
                    ConversationHandler.END: ConversationHandler.END,
                    RCS.MAIN_BACKER: RCS.MAIN_BACKER
                }
            ),
            ConversationHandler(
                entry_points=[CallbackQueryHandler(pattern="software", callback=request_router)],
                states={
                    RCS.REQUEST_NAME: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
                    RCS.REQUEST_LINK: [MessageHandler(filters=filters.Entity("url"), callback=request_detail)],
                    RCS.REQUEST_VERSION: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
                    RCS.REQUEST_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=recheck_request)],
                    RCS.CHECK_REQUEST: [
                        CallbackQueryHandler(
                            pattern="confirm_request",
                            callback=confirm_request
                        ),
                        CallbackQueryHandler(
                            pattern="^edit_.+$",
                            callback=edit_request_detail
                        )
                    ],
                    RCS.EDIT_NAME: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_LINK: [MessageHandler(filters=filters.Entity("url"), callback=edited_detail)],
                    RCS.EDIT_VERSION: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
                    RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)]
                },
                fallbacks=[CallbackQueryHandler(pattern="^back_.+$", callback=backer)],
                map_to_parent={
                    ConversationHandler.END: ConversationHandler.END,
                    RCS.MAIN_BACKER: RCS.MAIN_BACKER
                }
            )
        ],
    },
    fallbacks=[CallbackQueryHandler(pattern="^back_.+$", callback=backer)],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    }
)


private_conversation_handler = ConversationHandler(
    entry_points=[
        PrefixHandler([".", "/", "!"], "start", start)
    ],
    states={
        # User main router
        PCS.USER_CONVERSATION: [close_button_handler, CallbackQueryHandler(callback=user_main_router)],
        # Admin main router
        PCS.ADMIN_CONVERSATION: [close_button_handler, CallbackQueryHandler(callback=admin_main_router)],
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
        PCS.NEW_REQUEST: [android_request_handler, windows_request_handler, ios_request_handler, macos_request_handler]
    },
    fallbacks=[CallbackQueryHandler(callback=user_main_router)],
    allow_reentry=True
)
