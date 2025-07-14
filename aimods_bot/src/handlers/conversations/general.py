from telegram.ext import CallbackQueryHandler
from aimods_bot.src.helpers.utils.alerts import open_private_alert


alert_handler = CallbackQueryHandler(
    callback=open_private_alert,
    pattern=r"^alert_.+"
)