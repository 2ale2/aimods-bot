from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from aimods_bot.src.core.reboot import reboot
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.utils.file_utils import set_data_in_json
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete


async def test_mode_command(update: Update, context: CallbackContext):
    await safe_delete(update=update, context=context)
    args = context.args
    if not args or args[0].lower() not in ("on", "off"):
        await send_temporary_message(
            update=update,
            context=context,
            text="⚠ Indica <code>On</code> o <code>Off</code> come parametro del comando.",
            recipient_id=update.effective_user.id,
            delay_delete=5
        )
        return

    if args[0] == "on":
        set_data_in_json("test_mode", True)
    else:
        set_data_in_json("test_mode", False)

    await reboot(update=update, context=context)
