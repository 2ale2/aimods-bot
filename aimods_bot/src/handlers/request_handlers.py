from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters

from aimods_bot.src.callbacks.panels.user import user_main_router
from aimods_bot.src.callbacks.panels.user.request.request import request_detail, recheck_request, \
    confirm_request, edit_request_detail, edited_detail, backer
from aimods_bot.src.callbacks.panels.user.request.route import request_category, request_router
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS, \
    PrivateConversationState as PCS

windows_game_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(pattern="^user/add_request/windows/game/from_notification$", callback=user_main_router),
        CallbackQueryHandler(pattern="^game$", callback=request_router)],
    states={
        RCS.REQUEST_NAME: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
        RCS.REQUEST_LINK: [MessageHandler(filters=filters.Entity("url"), callback=request_detail)],
        RCS.REQUEST_VERSION: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
        RCS.REQUEST_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
        RCS.REQUEST_STEAMTOOLS: [CallbackQueryHandler(pattern="^bool_.+", callback=recheck_request)],
        RCS.CHECK_REQUEST: [
            CallbackQueryHandler(
                pattern="confirm_request",
                callback=confirm_request
            ),
            CallbackQueryHandler(
                pattern="^(?:edit_|bool_).+",
                callback=edit_request_detail
            ),
        ],
        RCS.EDIT_NAME: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
        RCS.EDIT_LINK: [MessageHandler(filters=filters.Entity("url"), callback=edited_detail)],
        RCS.EDIT_VERSION: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
        RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)]
    },
    fallbacks=[
        CallbackQueryHandler(pattern="^reset_conversation$", callback=user_main_router),
        CallbackQueryHandler(pattern=r"^(?:back_(?!category\b).+|no_edit)$", callback=backer)
    ],
    map_to_parent={
        ConversationHandler.END: ConversationHandler.END,
        RCS.MAIN_BACKER: RCS.MAIN_BACKER,
        RCS.REQUEST_CATEGORY: RCS.REQUEST_CATEGORY
    },
    name="windows_request_game_conversation",
    allow_reentry=True,
    persistent=True
)

windows_adobe_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(pattern="^user/add_request/windows/adobe/from_notification$", callback=user_main_router),
        CallbackQueryHandler(pattern="^adobe$", callback=request_router)
    ]
    ,
    states={
        RCS.REQUEST_NAME: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
        RCS.REQUEST_VERSION: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
        RCS.REQUEST_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=request_detail)],
        RCS.REQUEST_ARCH: [CallbackQueryHandler(pattern="^bool_.+", callback=recheck_request)],
        RCS.CHECK_REQUEST: [
            CallbackQueryHandler(
                pattern="confirm_request",
                callback=confirm_request
            ),
            CallbackQueryHandler(
                pattern="^(?:edit_|bool_).+",
                callback=edit_request_detail
            )
        ],
        RCS.EDIT_NAME: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
        RCS.EDIT_LINK: [MessageHandler(filters=filters.Entity("url"), callback=edited_detail)],
        RCS.EDIT_VERSION: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
        RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)],
    },
    fallbacks=[
        CallbackQueryHandler(pattern="^reset_conversation$", callback=user_main_router),
        CallbackQueryHandler(pattern=r"^(?:back_(?!category\b).+|no_edit)$", callback=backer)
    ],
    map_to_parent={
        ConversationHandler.END: ConversationHandler.END,
        RCS.MAIN_BACKER: RCS.MAIN_BACKER,
        RCS.REQUEST_CATEGORY: RCS.REQUEST_CATEGORY
    },
    name="windows_adobe_request_conversation",
    allow_reentry=True,
    persistent=True
)

windows_daw_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(pattern="^user/add_request/windows/daw/from_notification$", callback=user_main_router),
        CallbackQueryHandler(pattern="^daw$", callback=request_router)
    ],
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
    fallbacks=[
        CallbackQueryHandler(pattern="^reset_conversation$", callback=user_main_router),
        CallbackQueryHandler(pattern=r"^(?:back_(?!category\b).+|no_edit)$", callback=backer)
    ],
    map_to_parent={
        ConversationHandler.END: ConversationHandler.END,
        RCS.MAIN_BACKER: RCS.MAIN_BACKER,
        RCS.REQUEST_CATEGORY: RCS.REQUEST_CATEGORY
    },
    name="windows_daw_request_conversation",
    allow_reentry=True,
    persistent=True
)

windows_software_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(pattern="^user/add_request/windows/software/from_notification$", callback=user_main_router),
        CallbackQueryHandler(pattern="^software$", callback=request_router)
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
        RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)]
    },
    fallbacks=[
        CallbackQueryHandler(pattern="^reset_conversation$", callback=user_main_router),
        CallbackQueryHandler(pattern=r"^(?:back_(?!category\b).+|no_edit)$", callback=backer)
    ],
    map_to_parent={
        ConversationHandler.END: ConversationHandler.END,
        RCS.MAIN_BACKER: RCS.MAIN_BACKER,
        RCS.REQUEST_CATEGORY: RCS.REQUEST_CATEGORY
    },
    name="windows_software_request_conversation",
    allow_reentry=True,
    persistent=True
)

macos_daw_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(pattern="^user/add_request/macos/daw/from_notification$", callback=user_main_router),
        CallbackQueryHandler(pattern="daw", callback=request_router)
    ],
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
    fallbacks=[
        CallbackQueryHandler(pattern="^reset_conversation$", callback=user_main_router),
        CallbackQueryHandler(pattern=r"^back_(?!category\b).+", callback=backer)
    ],
    map_to_parent={
        ConversationHandler.END: ConversationHandler.END,
        RCS.MAIN_BACKER: RCS.MAIN_BACKER
    },
    name="macos_request_daw_conversation",
    allow_reentry=True,
    persistent=True
)

macos_software_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(pattern="^user/add_request/macos/software/from_notification$", callback=user_main_router),
        CallbackQueryHandler(pattern="software", callback=request_router)
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
        RCS.EDIT_FUNCTIONALITIES: [MessageHandler(filters=filters.TEXT, callback=edited_detail)]
    },
    fallbacks=[
        CallbackQueryHandler(pattern="^reset_conversation$", callback=user_main_router),
        CallbackQueryHandler(pattern=r"^back_(?!category\b).+", callback=backer)
    ],
    map_to_parent={
        ConversationHandler.END: ConversationHandler.END,
        RCS.MAIN_BACKER: RCS.MAIN_BACKER
    },
    name="macos_request_software_conversation",
    allow_reentry=True,
    persistent=True
)

android_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(pattern="^user/add_request/android/app/from_notification$", callback=user_main_router),
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
    fallbacks=[
        CallbackQueryHandler(pattern="^reset_conversation$", callback=user_main_router),
        CallbackQueryHandler(pattern=r"^(?:back_(?!category\b).+|no_edit)$", callback=backer)
    ],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    },
    name="android_request_conversation",
    persistent=True,
    allow_reentry=True
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
            windows_game_request_handler,
            windows_adobe_request_handler,
            windows_daw_request_handler,
            windows_software_request_handler
        ],
    },
    fallbacks=[
        CallbackQueryHandler(pattern="^reset_conversation$", callback=user_main_router),
        CallbackQueryHandler(pattern=r"^back_category$", callback=request_category),
        CallbackQueryHandler(pattern="^back_.+$", callback=backer)
    ],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    },
    name="windows_request_conversation",
    persistent=True
)

ios_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(pattern="^user/add_request/ios/app/from_notification$", callback=user_main_router),
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
    fallbacks=[
        CallbackQueryHandler(pattern="^reset_conversation$", callback=user_main_router),
        CallbackQueryHandler(pattern=r"^back_(?!category\b).+", callback=backer)
    ],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    },
    name="ios_request_conversation",
    persistent=True,
    allow_reentry=True
)

macos_request_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            pattern="user/add_request/macos",
            callback=request_category
        )
    ],
    states={
        RCS.REQUEST_CATEGORY: [macos_daw_request_handler, macos_software_request_handler],
    },
    fallbacks=[
        CallbackQueryHandler(pattern="^reset_conversation$", callback=user_main_router),
        CallbackQueryHandler(pattern=r"^back_category$", callback=request_category),
        CallbackQueryHandler(pattern="^back_.+$", callback=backer)
    ],
    map_to_parent={
        RCS.MAIN_BACKER: PCS.NEW_REQUEST,
        ConversationHandler.END: PCS.USER_CONVERSATION
    },
    name="macos_request_conversation",
    persistent=True
)
