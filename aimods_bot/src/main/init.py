import logging
import os
import locale
import sys
from telegram.ext import ApplicationBuilder
from aimods_bot.src.core.persistence import PostgresPersistence
from aimods_bot.src.core.setup import set_application_data, get_handlers
from aimods_bot.src.core.shutdown import post_shutdown
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.core.exceptions import ConfigError

locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')

log = logger.getChild("init")

logging.getLogger('httpx').setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        log.error("BOT_TOKEN non impostato")
        sys.exit(1)

    application = (
        ApplicationBuilder()
        .token(bot_token)
        .persistence(PostgresPersistence(url=os.getenv("POSTGRES_CONNECTION_URL")))
        .arbitrary_callback_data(True)
        .post_init(set_application_data)
        .post_shutdown(post_shutdown)
        .build()
    )

    handlers = get_handlers()
    application.add_handlers(handlers)

    try:
        application.run_webhook(
            listen="0.0.0.0",
            port=8080,
            url_path="bot",
            webhook_url=f"https://bot.aimodsitalia.store/bot"
        )
        r = application.bot_data.get("restart", False)
        if r.get("toggle", False):
            application.bot_data["restart"]["toggle"] = False
            os.execl(sys.executable, sys.executable, *sys.argv)
    except ConfigError as e:
        log.error(f"Config validation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
