from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.core.config_accessor import set_value


async def toggle_antiflood(update: Update, context: CallbackContext):
    bool_value = update.callback_query.data.split("_")[-1] == "true"
    set_value(context=context, path="moderation.antiflood", value=bool_value)
