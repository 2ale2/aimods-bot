from telegram.ext import CommandHandler
import handlers_function


def create_handlers() -> list:
    """Crea gli handler e li pone all'interno di una lista; poi la ritorna."""
    handlers = list()

    # - command handlers
    # -- start command
    handlers.append(CommandHandler("start", handlers_function.start_command))

    return handlers
