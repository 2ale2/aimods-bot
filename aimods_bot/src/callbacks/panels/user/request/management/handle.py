from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.constants.models import RequestStatus
from aimods_bot.src.helpers.utils.request_utils import edit_request_status
from aimods_bot.src.helpers.utils.telegram_utils import str_id_to_int


async def cancel_request(context: ContextTypes.DEFAULT_TYPE, ix: int):
    ix = str_id_to_int(ix)
    await edit_request_status(context=context, ix=ix, status=RequestStatus.CANCELLED)
