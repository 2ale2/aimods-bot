import subprocess
from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.utils.file_utils import set_data_in_json


async def reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        set_data_in_json(key=["restarting", "toggle"], value=True)
        set_data_in_json(key=["restarting", "user_id"], value=update.effective_user.id)
        await context.application.stop_running()
        await context.application.shutdown()
        # il bot dovrebbe riavviarsi a questo punto
        # necessario creare un servizio e poi usare
        # subprocess.run(["systemctl", "restart", "mybot"])
    except Exception as e:
        print(e)
