import aimods_bot.src.core.constants as constants
from telegram.ext import Application


async def post_shutdown(application: Application):
    if constants.pyro_instance:
        await constants.pyro_instance.stop()
