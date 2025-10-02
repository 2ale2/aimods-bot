from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import RestartData


async def reboot(update: Update, context: CustomContext):
    try:
        context.pydb.restart = RestartData(toggle=True, user_id=update.effective_user.id)
        await context.application.stop_running()
    except Exception as e:
        print(e)
