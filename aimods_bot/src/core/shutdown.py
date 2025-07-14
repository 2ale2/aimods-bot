import aimods_bot.src.helpers.constants.constants as constants
from telegram.ext import Application


async def post_shutdown(application: Application):
    await constants.pyro_instance.stop()
