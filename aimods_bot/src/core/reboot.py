import subprocess
from telegram import Update
from telegram.ext import ContextTypes


async def reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.bot_data["restart"] = {
            "toggle": True,
            "user_id": update.effective_user.id
        }
        await context.application.stop_running()
    except Exception as e:
        print(e)
