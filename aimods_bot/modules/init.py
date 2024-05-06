import logging

from aimods_bot.modules import handlers

from telegram.warnings import PTBDeprecationWarning
from telegram.ext import ApplicationBuilder, ContextTypes
from aimods_bot.modules import core

logging.getLogger('httpx').setLevel(logging.WARNING)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def main():
    application = ApplicationBuilder().token(core.return_env("BOT_TOKEN")).build()

    application.add_handlers(handlers.create_handlers())

    application.run_polling()


if __name__ == '__main__':
    main()
