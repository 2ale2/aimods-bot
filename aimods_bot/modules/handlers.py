from telegram import Update
from telegram.ext import (MessageHandler, CallbackQueryHandler,
                          ConversationHandler, ChatJoinRequestHandler, filters, TypeHandler)

from constants import ChannelMessageForRecapFilter, ModerationSettingsStates

import handlers_function
import utils

RULES_ACCEPTED = 0


def create_handlers() -> list:
    """Crea gli handler e li pone all'interno di una lista; poi la ritorna."""
    # noinspection PyListCreation
    handlers = []

    # - test handler, for testing and debugging purposes only. it reroutes every update!
    # handlers.append(
    #     TypeHandler(
    #         type=Update,
    #         callback=handlers_function.test
    #     )
    # )

    channel_message_for_recap_filter = ChannelMessageForRecapFilter()

    # - cattura post canale
    handlers.append(
        MessageHandler(
            filters=filters.Chat(chat_id=-1002544860500) & channel_message_for_recap_filter,
            callback=handlers_function.catch_post_from_channel
        )
    )

    # - commands handler
    handlers.append(
        MessageHandler(
            filters=(filters.TEXT | filters.CAPTION)
            & (filters.Regex(r"^[/.!]") | filters.CaptionRegex(r"^[/.!]")),
            callback=handlers_function.handle_command)
    )

    # - callback query handlers
    handlers.append(CallbackQueryHandler(callback=utils.open_private_alert,pattern="^alert.+$"))
    handlers.append(CallbackQueryHandler(callback=utils.callback_close_message, pattern="^close.*$"))

    # - conversation handlers
    # -- double check at join
    handlers.append(ConversationHandler(
        entry_points=[
            ChatJoinRequestHandler(callback=handlers_function.new_member_joined_forum),
            CallbackQueryHandler(
                callback=handlers_function.new_member_joined_forum,
                pattern="^recreate_captcha$"
            )
        ],
        states={
            RULES_ACCEPTED: [
                CallbackQueryHandler(
                    callback=handlers_function.new_member_accepted_the_rules,
                    pattern="^accept_rules.+$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(callback=handlers_function.new_member_joined_forum, pattern="^recreate_captcha$")
        ],
        per_chat=False,
        name="join_handler",
        persistent=True
    ))

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
            ]
        },
        fallbacks=[],
        map_to_parent={
            ConversationHandler.END: ModerationSettingsStates.SECURITY_FILTERS_CHOICE
        },
        allow_reentry=True
    )

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

    # -- moderation settings menu
    handlers.append(ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback=handlers_function.moderation_settings, pattern="^moderation$"),
        ],
        states={
            ModerationSettingsStates.MAIN_MENU_CHOICE: [
                CallbackQueryHandler(
                    callback=handlers_function.moderation_settings,
                    pattern="^(security_filters_settings|user_moderation_settings|"
                            "media_contents_settings|community_settings)$"
                ),
                CallbackQueryHandler(callback=handlers_function.start_command, pattern="^main_menu$")
            ],
            ModerationSettingsStates.SECURITY_FILTERS_CHOICE: [
                antispam_settings_conversation_handler,
                antiflood_settings_conversation_handler
            ],

        },
        fallbacks=[],
        allow_reentry=True
    ))

    return handlers
