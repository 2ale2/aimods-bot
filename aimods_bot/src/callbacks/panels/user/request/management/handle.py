from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import RequestStatus
from aimods_bot.src.helpers.utils.request_utils import edit_request_status


async def cancel_request(context: CustomContext, ix: int):
    await edit_request_status(context=context, ix=ix, status=RequestStatus.CANCELLED)
