from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import RequestStatus


async def cancel_request(context: CustomContext, ix: int):
    await context.edit_request_status(ix=ix, status=RequestStatus.CANCELLED)
