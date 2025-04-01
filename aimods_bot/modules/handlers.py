from telegram.ext import (MessageHandler, CallbackQueryHandler,
                          ConversationHandler, ChatJoinRequestHandler, filters)

import handlers_function
import utils

RULES_ACCEPTED = 0


def create_handlers() -> list:
    """Crea gli handler e li pone all'interno di una lista; poi la ritorna."""
    # noinspection PyListCreation
    handlers = []

    # - command handlers
    handlers.append(MessageHandler(filters.TEXT & filters.Regex(r"^[/.!]"), callback=handlers_function.handle_command))

    # - callback query handlers
    handlers.append(CallbackQueryHandler(callback=utils.open_private_alert,pattern="^alert.+$"))
    handlers.append(CallbackQueryHandler(callback=handlers_function.callback_close_message, pattern="^close.+$"))

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
            RULES_ACCEPTED: [CallbackQueryHandler(callback=handlers_function.new_member_accepted_the_rules,pattern="^accept_rules.+$")]
        },
        fallbacks=[
            CallbackQueryHandler(callback=handlers_function.new_member_joined_forum,pattern="^recreate_captcha$")
        ],
        per_chat=False,
        name="join_handler",
        persistent=True
    ))

    return handlers
