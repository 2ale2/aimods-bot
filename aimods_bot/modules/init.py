import logging

from telegram.ext import ApplicationBuilder

from aimods_bot.modules import utils, core, handlers
from aimods_bot.modules.persistence import PostgresPersistence
from aimods_bot.modules.constants import Scopes

logging.getLogger('httpx').setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

SCOPES = Scopes()


def main():
    application = ApplicationBuilder().token(utils.get_env("BOT_TOKEN")).persistence(
        PostgresPersistence(url=utils.get_env("POSTGRES_CONNECTION_URL"))
    ).post_init(core.set_application_data).build()

    application.add_handlers(handlers.create_handlers())

    application.run_polling()


if __name__ == '__main__':
    main()
