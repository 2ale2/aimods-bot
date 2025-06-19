from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from aimods_bot.modules.constants import ModerationSettingsStates
from aimods_bot.modules import handlers_function
from aimods_bot.modules.handlers_package.moderation.punishment_duration_handler import set_punishment_duration_handler


antispam_edit_list_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(callback=handlers_function.antispam_set_link_list, pattern="antispam_set_link_.*")
    ],
    states={
        ModerationSettingsStates.ANTISPAM_EDIT_LIST: [
            CallbackQueryHandler(
                callback=handlers_function.antispam_set_link_list,
                pattern="^(antispam_view|antispam_add|antispam_remove).*|^antispam_set_links$",
            )
        ],
        ModerationSettingsStates.ANTISPAM_EDIT_LINK_LIST: [
            MessageHandler(
                callback=handlers_function.antispam_set_link_list,
                filters=filters.TEXT
            )
        ]
    },
    fallbacks=[],
    allow_reentry=True,
    map_to_parent={
        ConversationHandler.END: ModerationSettingsStates.ANTISPAM_SET_LINK
    }
)


antispam_settings_conversation_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback=handlers_function.antispam_settings, pattern="^antispam_settings$")],
        states={
            ModerationSettingsStates.ANTISPAM_MAIN_PANEL: [
                CallbackQueryHandler(
                    callback=handlers_function.antispam_settings,
                    pattern="^(antispam_toggle_on|antispam_toggle_off|"
                            "antispam_set_punishment|antispam_set_links|antispam_set_media|security_filters_settings)$"
                )
            ],
            ModerationSettingsStates.SET_PUNISHMENT: [
                set_punishment_duration_handler,
                CallbackQueryHandler(
                    callback=handlers_function.antispam_settings,
                    pattern="^antispam_set_punishment_.*|^antispam_settings$"
                )
            ],
            ModerationSettingsStates.ANTISPAM_SET_LINK: [
                CallbackQueryHandler(
                    callback=handlers_function.antispam_settings,
                    pattern="^antispam_set_link_allow_after.*|^antispam_set_links$"
                ),
                antispam_edit_list_conversation_handler
            ]
        },
        fallbacks=[],
        map_to_parent={
            ConversationHandler.END: ModerationSettingsStates.SECURITY_FILTERS_CHOICE
        },
        allow_reentry=True
    )