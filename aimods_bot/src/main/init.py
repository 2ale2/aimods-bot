import logging
import os
import sys
from telegram.ext import ApplicationBuilder
from aimods_bot.src.core.persistence import PostgresPersistence
from aimods_bot.src.core.setup import set_application_data
from aimods_bot.src.core.shutdown import post_shutdown
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.core.exceptions import ConfigError
from aimods_bot.src.handlers.collect import all_handlers

log = logger.getChild("init")

logging.getLogger('httpx').setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).persistence(
        PostgresPersistence(url=os.getenv("POSTGRES_CONNECTION_URL"))
    ).post_init(set_application_data).post_shutdown(post_shutdown).build()

    application.add_handlers(all_handlers)
    try:
        application.run_polling()
    except ConfigError as e:
        log.error(f"Config validation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
