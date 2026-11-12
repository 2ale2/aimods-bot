from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.infra.log import logger
from aimods_bot.src.features.requests.models import BaseRequest

log = logger.getChild(__name__)


async def toggle_status_notifications(context: CustomContext, request: BaseRequest) -> bool:
    """Inverte le notifiche di cambio stato e le salva. Restituisce False se il salvataggio non è riuscito."""
    if not request.is_active:
        return False
    enabled = not request.status_change_notifications
    ok = await context.set_request_status_change_notifications(ix=request.id, enabled=enabled)
    if ok:
        log.debug(f"{context.user_id} changed status notifications to {enabled} for request {request.id}")
    return ok
