import logging
import os
import core
import sys
import handlers

from loggers import bot_logger

from telegram.ext import ApplicationBuilder
from persistence import PostgresPersistence
from exceptions import ConfigValidationError

logging.getLogger('httpx').setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).persistence(
        PostgresPersistence(url=os.getenv("POSTGRES_CONNECTION_URL"))
    ).post_init(core.set_application_data).post_shutdown(core.post_shutdown).build()

    application.add_handlers(handlers.create_handlers())
    try:
        application.run_polling()
    except ConfigValidationError as e:
        bot_logger.error(f"Config validation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
