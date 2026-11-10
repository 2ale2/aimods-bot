from typing import Awaitable, Callable

from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.features.requests.admin.contact.handle import notify_author
from aimods_bot.src.features.requests.admin.contact.render import (
    render_admin_contact_author_panel, render_admin_notify_author_confirmation_panel,
)
from aimods_bot.src.features.requests.models import BaseRequest
from aimods_bot.src.infra.log import logger
from aimods_bot.src.ui.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.ui.path_navigation import AdminRequestManagementRoute, GlobalAction
from aimods_bot.src.ui.routing import PathBuilder

log = logger.getChild(__name__)


async def route_admin_contact_author(
        update: Update,
        context: CustomContext,
        request: BaseRequest,
        root: PathBuilder,
        relative_path: PathBuilder,
        render_request_panel: Callable[[], Awaitable[None]]
):
    """
    <richiesta>/contact_author[/notify_author[/yes]]

    `render_request_panel` ridisegna il pannello della richiesta dopo l'invio dell'avviso.
    """
    match relative_path.segments:
        case []:
            await render_admin_contact_author_panel(update=update, context=context, request=request, base_path=root)

        case [AdminRequestManagementRoute.NOTIFY_AUTHOR]:
            await render_admin_notify_author_confirmation_panel(
                update=update,
                context=context,
                request=request,
                base_path=root.add(AdminRequestManagementRoute.NOTIFY_AUTHOR)
            )

        case [AdminRequestManagementRoute.NOTIFY_AUTHOR, GlobalAction.YES]:
            if await notify_author(update=update, context=context, request=request):
                await render_request_panel()
            else:
                await render_admin_contact_author_panel(
                    update=update, context=context, request=request, base_path=root
                )

        case _:
            log.warning(f"Unhandled path in contact author: {relative_path.build()}")

    return PCS.ADMIN_CONVERSATION
