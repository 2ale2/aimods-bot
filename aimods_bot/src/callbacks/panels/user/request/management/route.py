from telegram import Update

from aimods_bot.src.callbacks.panels.general.user_archive.route import route_user_archive
from aimods_bot.src.callbacks.panels.user.request.management.handle import toggle_status_notifications
from aimods_bot.src.callbacks.panels.user.request.management.render import \
    render_manage_selected_request_panel, render_user_request_management_panel, \
    render_user_manage_active_requests_panel, render_confirm_cancel_panel, render_request_cancelled_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import RequestStatus
from aimods_bot.src.helpers.constants.path_navigation import UserManageRequestsRoute, GlobalAction
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder

log = logger.getChild(__name__)


async def user_request_management_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_user_request_management_panel(update=update, context=context, base_path=root)
            return PCS.USER_CONVERSATION

        case [UserManageRequestsRoute.ACTIVE, *rest]:
            return await user_active_requests_management_route(
                update=update,
                context=context,
                root=root.add(UserManageRequestsRoute.ACTIVE),
                relative_path=PathBuilder(*rest)
            )
        case UserManageRequestsRoute.REQUEST_ARCHIVE:
            await route_user_archive(
                update=update,
                context=context,
                root=root.add(UserManageRequestsRoute.REQUEST_ARCHIVE),
                relative_path=PathBuilder()  # Misura di sicurezza: forzo [] per forzare il ramo corretto del router
            )
            return PCS.USER_CONVERSATION


async def user_active_requests_management_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_user_manage_active_requests_panel(update=update, context=context, base_path=root)

        case [request_id, *rest] if request_id.isnumeric():
            request = context.get_active_request_by_id(ix=int(request_id))

            match PathBuilder(*rest).segments:
                case []:
                    if not request:
                        log.warning(f"Active request {request_id} from user {update.effective_user.id} not found")
                        await update.callback_query.answer(
                            text="⚠️ Attenzione\n\n"
                                 "Questa richiesta non è stata trovata. Non dovrebbe accadere, quindi informa un admin "
                                 "di questo problema. Grazie mille.",
                            show_alert=True
                        )
                        await render_user_manage_active_requests_panel(update=update, context=context, base_path=root)
                    else:
                        await render_manage_selected_request_panel(
                            update=update,
                            context=context,
                            base_path=root.add(request_id),
                            request=request
                        )

                case [toggle_notification] if toggle_notification in (
                    UserManageRequestsRoute.ENABLE_STATUS_NOTIFICATION,
                    UserManageRequestsRoute.DISABLE_STATUS_NOTIFICATION
                ):
                    await toggle_status_notifications(context=context, request=request)
                    await render_manage_selected_request_panel(
                        update=update,
                        context=context,
                        base_path=root.add(request_id),
                        request=request
                    )

                case [UserManageRequestsRoute.CANCEL]:
                    await render_confirm_cancel_panel(
                        update=update,
                        context=context,
                        base_path=root.add(request_id, UserManageRequestsRoute.CANCEL),
                        request=request
                    )

                case [UserManageRequestsRoute.CANCEL, GlobalAction.YES]:
                    await context.edit_request_status(ix=request.id, status=RequestStatus.CANCELLED)
                    await render_request_cancelled_panel(
                        update=update,
                        context=context,
                        base_path=root
                    )

    return PCS.USER_CONVERSATION
