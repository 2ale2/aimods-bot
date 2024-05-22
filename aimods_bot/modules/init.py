import logging
import warnings

from telegram.ext import ApplicationBuilder
from telegram.warnings import PTBDeprecationWarning

from aimods_bot.modules import core
from aimods_bot.modules.persistence import PostgresPersistence
from aimods_bot.modules import handlers
from aimods_bot.modules.constants import Scopes

logging.getLogger('httpx').setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

warnings.simplefilter('always', PTBDeprecationWarning)

SCOPES = Scopes()


def main():
    application = ApplicationBuilder().token(core.get_env("BOT_TOKEN")).persistence(
        PostgresPersistence(url=core.get_env("POSTGRES_CONNECTION_URL"))
    ).post_init(core.set_application_data).build()

    application.add_handlers(handlers.create_handlers())

    application.run_polling()


if __name__ == '__main__':
    main()
