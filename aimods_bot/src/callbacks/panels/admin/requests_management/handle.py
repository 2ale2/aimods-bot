from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import RequestStatus, RejectRequestReason


async def confirm_rejection(context: CustomContext, ix: int, reason: RejectRequestReason | str):
    final_reason = RejectRequestReason(reason) if isinstance(reason, RejectRequestReason) else reason

    await context.edit_request_status(
        ix=ix,
        status=RequestStatus.REJECTED,
        rejection_reason=final_reason
    )
