from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.constants.models import RequestStatus
from aimods_bot.src.helpers.utils.request_utils import edit_request_status


async def cancel_request(context: ContextTypes.DEFAULT_TYPE, ix: str):
    await edit_request_status(context=context, ix=ix, status=RequestStatus.CANCELLED)
