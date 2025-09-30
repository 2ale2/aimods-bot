import logging
import os
import locale
import sys
from telegram.ext import ApplicationBuilder, ContextTypes, PersistenceInput, Application
from aimods_bot.src.core.async_persistence import AsyncPostgresPersistence
from aimods_bot.src.core.customcontext import CustomContext, BotData
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

    persistence = AsyncPostgresPersistence(
        url=os.getenv("POSTGRES_CONNECTION_URL"),
        on_flush=False,
        coalesce_delay=0.1,
        store_data = PersistenceInput(chat_data=False, user_data=False)
    )

    context_types = ContextTypes(context=CustomContext, bot_data=BotData)

    async def post_init_hook(app):
        await persistence.initialize()  # crea pool + carica dati nel loop PTB
        await set_application_data(app)

    async def post_shutdown_hook(app):
        await post_shutdown(app)
        await persistence.aclose()

    application = (
        ApplicationBuilder()
        .token(bot_token)
        .persistence(persistence)
        .arbitrary_callback_data(True)
        .context_types(context_types=context_types)
        .post_init(post_init_hook)
        .post_shutdown(post_shutdown_hook)
        .build()
    )

    handlers = get_handlers()
    application.add_handlers(handlers)

    try:
        application.run_polling()
        # application.run_webhook(
        #     listen="0.0.0.0",
        #     port=8080,
        #     url_path="bot",
        #     webhook_url=f"https://bot.aimodsitalia.store/bot"
        # )
        r = application.bot_data.restart
        if r and r.toggle:
            application.bot_data["restart"]["toggle"] = False
            os.execl(sys.executable, sys.executable, *sys.argv)
    except ConfigError as e:
        log.error(f"Config validation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
