from telegram.ext import ConversationHandler, CallbackQueryHandler
from aimods_bot.modules.globals import ModerationSettingsStates
from aimods_bot.modules import handlers_function
from aimods_bot.modules.handlers_package.moderation.punishment_duration_handler import set_punishment_duration_handler


antiflood_settings_conversation_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback=handlers_function.antiflood_settings, pattern="^antiflood_settings$"),
        ],
        states={
            ModerationSettingsStates.ANTIFLOOD_MAIN_PANEL: [
                CallbackQueryHandler(
                    callback=handlers_function.antiflood_settings,
                    pattern="^(antiflood_toggle_.*|antiflood_set_.*|security_filters_settings)$"
                )
            ],
            ModerationSettingsStates.SET_PUNISHMENT: [
                set_punishment_duration_handler,
                CallbackQueryHandler(
                    callback=handlers_function.antiflood_settings,
                    pattern="^antiflood_set_punishment_.*"
                )
            ],
            ModerationSettingsStates.ANTIFLOOD_SET_LIMITS: [
                CallbackQueryHandler(
                    callback=handlers_function.antiflood_settings,
                    pattern="^(antiflood_set_timemessages_.+|antiflood_set_numbermessages_.+)$"
                )
            ]
        },
        fallbacks=[],
        allow_reentry=True,
        map_to_parent={
            ConversationHandler.END: ModerationSettingsStates.SECURITY_FILTERS_CHOICE
        }
    )