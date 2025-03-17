from telegram.ext import (CommandHandler, MessageHandler, CallbackQueryHandler,
                          ConversationHandler, ChatJoinRequestHandler, filters)

import handlers_function

RULES_ACCEPTED = 0


def create_handlers() -> list:
    """Crea gli handler e li pone all'interno di una lista; poi la ritorna."""
    handlers = []

    # - command handlers
    # -- start command
    handlers.append(CommandHandler("start", callback=handlers_function.start_command))

    # -- rules command
    handlers.append(CommandHandler("rules", callback=handlers_function.send_rules))
    # -- delete message command
    handlers.append(CommandHandler("del", callback=handlers_function.delete_group_message))
    handlers.append(MessageHandler(filters=filters.TEXT & filters.Regex(r'^\.del'),
                                   callback=handlers_function.delete_group_message))
    handlers.append(MessageHandler(filters=filters.TEXT & filters.Regex('^!del'),
                                   callback=handlers_function.delete_group_message))
    handlers.append(CallbackQueryHandler(callback=handlers_function.alert_del_message_not_selected,
                                         pattern="^open_private_alert.+$"))

    handlers.append(CommandHandler("limit", callback=handlers_function.limit_user))

    # - conversation handlers
    # -- double check at join
    handlers.append(ConversationHandler(
        entry_points=[ChatJoinRequestHandler(callback=handlers_function.new_member_joined_forum),
                      CommandHandler("request", callback=handlers_function.new_member_joined_forum)],
        states={
            RULES_ACCEPTED: [CallbackQueryHandler(callback=handlers_function.new_member_accepted_the_rules,
                                                  pattern="^accept_rules.+$")]
        },
        fallbacks=[CommandHandler("request", callback=handlers_function.new_member_joined_forum)],
        per_chat=False,
        name="join_handler",
        persistent=True
    ))

    # - service handlers
    # -- delete message using inline keyboard
    handlers.append(CallbackQueryHandler(callback=handlers_function.callback_close_message, pattern="^close.+$"))

    return handlers
