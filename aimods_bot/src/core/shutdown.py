from aimods_bot.src.helpers import constants
from telegram.ext import Application


async def post_shutdown(application: Application):
    await constants.pyro_instance.stop()
