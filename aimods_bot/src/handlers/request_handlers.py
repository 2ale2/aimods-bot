from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters

from aimods_bot.src.callbacks.panels.user.request.request import request_detail, recheck_request, \
    confirm_request, edit_request_detail, edited_detail, backer
from aimods_bot.src.callbacks.panels.user.request.route import request_category, request_router
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS, \
    PrivateConversationState as PCS

android_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            pattern="user/add_request/android",
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
    fallbacks=[CallbackQueryHandler(pattern=r"^back_(?!category\b).+", callback=backer)],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    }
)
windows_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            pattern="user/add_request/windows",
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
                fallbacks=[CallbackQueryHandler(pattern=r"^back_(?!category\b).+", callback=backer)],
                map_to_parent={
                    ConversationHandler.END: ConversationHandler.END,
                    RCS.MAIN_BACKER: RCS.MAIN_BACKER,
                    RCS.REQUEST_CATEGORY: RCS.REQUEST_CATEGORY
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
                fallbacks=[CallbackQueryHandler(pattern=r"^back_(?!category\b).+", callback=backer)],
                map_to_parent={
                    ConversationHandler.END: ConversationHandler.END,
                    RCS.MAIN_BACKER: RCS.MAIN_BACKER,
                    RCS.REQUEST_CATEGORY: RCS.REQUEST_CATEGORY
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
                fallbacks=[CallbackQueryHandler(pattern=r"^back_(?!category\b).+", callback=backer)],
                map_to_parent={
                    ConversationHandler.END: ConversationHandler.END,
                    RCS.MAIN_BACKER: RCS.MAIN_BACKER,
                    RCS.REQUEST_CATEGORY: RCS.REQUEST_CATEGORY
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
                fallbacks=[CallbackQueryHandler(pattern=r"^back_(?!category\b).+", callback=backer)],
                map_to_parent={
                    ConversationHandler.END: ConversationHandler.END,
                    RCS.MAIN_BACKER: RCS.MAIN_BACKER,
                    RCS.REQUEST_CATEGORY: RCS.REQUEST_CATEGORY
                }
            )
        ],
    },
    fallbacks=[
        CallbackQueryHandler(pattern=r"^back_category$", callback=request_category),
        CallbackQueryHandler(pattern="^back_.+$", callback=backer)
    ],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    }
)
ios_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            pattern="user/add_request/ios",
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
    fallbacks=[CallbackQueryHandler(pattern=r"^back_(?!category\b).+", callback=backer)],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    }
)
macos_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            pattern="user/add_request/macos",
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
                fallbacks=[CallbackQueryHandler(pattern=r"^back_(?!category\b).+", callback=backer)],
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
                fallbacks=[CallbackQueryHandler(pattern=r"^back_(?!category\b).+", callback=backer)],
                map_to_parent={
                    ConversationHandler.END: ConversationHandler.END,
                    RCS.MAIN_BACKER: RCS.MAIN_BACKER
                }
            )
        ],
    },
    fallbacks=[
        CallbackQueryHandler(pattern=r"^back_category$", callback=request_category),
        CallbackQueryHandler(pattern="^back_.+$", callback=backer)
    ],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    }
)
