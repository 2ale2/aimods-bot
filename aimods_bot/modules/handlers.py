from telegram.ext import CommandHandler, ContextTypes
from telegram import Update


def create_handlers() -> list:
    """Crea gli handler e li pone all'interno di una lista; poi la ritorna."""
    handlers = list()

    # - command handlers
    # -- start command

    handlers.append(CommandHandler("start", start_command))

    return handlers


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello Staff A&I Mods! :)")
