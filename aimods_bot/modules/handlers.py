from telegram.ext import (CommandHandler, MessageHandler,
                          ConversationHandler, ChatJoinRequestHandler, filters, Application)
import handlers_function


def create_handlers(app: Application) -> list:
    """Crea gli handler e li pone all'interno di una lista; poi la ritorna."""
    handlers = list()

    # - command handlers
    # -- start command
    handlers.append(CommandHandler("start", handlers_function.start_command))

    # -- delete message command
    handlers.append(CommandHandler("del", handlers_function.delete_group_message))
    handlers.append(MessageHandler(filters=filters.TEXT & filters.Regex(r'^\.del'),
                                   callback=handlers_function.delete_group_message))
    handlers.append(MessageHandler(filters=filters.TEXT & filters.Regex('^!del'),
                                   callback=handlers_function.delete_group_message))
    join_handler = ConversationHandler(
        entry_points=[ChatJoinRequestHandler(callback=handlers_function.new_member_joined_forum,
                                             chat_id=app.bot_data["group_chat_id"])],
        states={},
        fallbacks=[]
    )
    return handlers
