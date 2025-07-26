from telegram import Update
from telegram.ext import CallbackContext
from aimods_bot.src.core.config_accessor import set_value


async def toggle_antispam(update: Update, context: CallbackContext):
    bool_value = update.callback_query.data.split("_")[-1] == "on"
    set_value(context=context, path="moderation.antispam.toggle", value=bool_value)
