from telegram import Update
from telegram.ext import (MessageHandler, CallbackQueryHandler,
                          ConversationHandler, ChatJoinRequestHandler, filters, TypeHandler)

from globals import ModerationSettingsStates
from handlers_package.moderation import antispam_handlers, antiflood_handlers
from handlers_package.channel_handlers import *
from handlers_package.commands_handlers import *

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

    # - cattura post canale
    handlers.append(channel_posts_capture_handler)

    # - commands handler
    handlers.append(commands_handler)

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
                antispam_handlers.antispam_settings_conversation_handler,
                antiflood_handlers.antiflood_settings_conversation_handler
            ],

        },
        fallbacks=[],
        allow_reentry=True
    ))

    return handlers
