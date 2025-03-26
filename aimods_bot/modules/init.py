import logging
import os

from telegram.ext import ApplicationBuilder

from aimods_bot.modules import core, handlers
from aimods_bot.modules.persistence import PostgresPersistence

logging.getLogger('httpx').setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).persistence(
        PostgresPersistence(url=os.getenv("POSTGRES_CONNECTION_URL"))
    ).post_init(core.set_application_data).build()

    application.add_handlers(handlers.create_handlers())

    application.run_polling()


if __name__ == '__main__':
    main()
