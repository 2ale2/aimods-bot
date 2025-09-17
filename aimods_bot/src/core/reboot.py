from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext


async def reboot(update: Update, context: CustomContext):
    try:
        context.bot_data["restart"] = {
            "toggle": True,
            "user_id": update.effective_user.id
        }
        await context.application.stop_running()
    except Exception as e:
        print(e)
