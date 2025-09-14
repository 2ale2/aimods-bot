from telegram import Update
from aimods_bot.src.core.config_accessor import set_value
from aimods_bot.src.core.customcontext import CustomContext


async def toggle_antiflood(update: Update, context: CustomContext):
    bool_value = update.callback_query.data.split("_")[-1] == "true"
    set_value(context=context, path="moderation.antiflood.toggle", value=bool_value)
