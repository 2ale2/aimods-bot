from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from aimods_bot.modules.globals import ModerationSettingsStates
from aimods_bot.modules import handlers_function

set_punishment_duration_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            callback=handlers_function.set_punishment_duration,
            pattern=".*_set_punishment_duration$")],
        states={
            ModerationSettingsStates.SET_PUNISHMENT_DURATION: [
                MessageHandler(
                    callback=handlers_function.set_punishment_duration,
                    filters=filters.TEXT
                ),
                CallbackQueryHandler(
                    callback=handlers_function.set_punishment_duration,
                    pattern=".*_set_punishment_.*|.*_set_punishment$"
                )
            ]
        },
        fallbacks=[],
        map_to_parent={
            ConversationHandler.END: ModerationSettingsStates.SET_PUNISHMENT
        }
    )