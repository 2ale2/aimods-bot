from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.requests import BaseRequest

log = logger.getChild(__name__)


async def toggle_status_notifications(context: CustomContext, request: BaseRequest):
    if not request.is_active:
        return
    request.status_change_notifications = not request.status_change_notifications
    log.debug(f"{context.user_id} changed status notifications to "
              f"{request.status_change_notifications} for request {request.id}")
