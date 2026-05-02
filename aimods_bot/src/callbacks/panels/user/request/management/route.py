from telegram import Update

from aimods_bot.src.callbacks.panels.general.user_archive.route import route_user_archive
from aimods_bot.src.callbacks.panels.user.request.management.handle import cancel_request, toggle_status_notifications
from aimods_bot.src.callbacks.panels.user.request.management.render import \
    render_active_request_panel, render_user_request_management_panel, render_user_manage_active_requests_panel, \
    render_confirm_cancel_panel, render_request_details_panel, render_request_cancelled_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_paths.navigation import UserManageRequestsRoute
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.models.routing import PathBuilder

from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import render_action_not_permitted_panel

log = logger.getChild(__name__)


async def user_request_management_route(update: Update, context: CustomContext, path: PathBuilder):
    match path.segments:
        case []:
            await render_user_request_management_panel(update=update, context=context)
            return PCS.USER_CONVERSATION
        case [UserManageRequestsRoute.ACTIVE, *rest]:
            return await user_active_requests_management_route(
                update=update,
                context=context,
                root=path.add(UserManageRequestsRoute.ACTIVE),
                relative_path=PathBuilder(*rest)
            )
        case UserManageRequestsRoute.REQUEST_ARCHIVE:
            await route_user_archive(
                update=update,
                context=context,
                root=path.add(UserManageRequestsRoute.REQUEST_ARCHIVE),
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
            await render_active_request_panel(update=update, context=context, base_path=root)
            return PCS.USER_CONVERSATION

        case [action, *rest]:
            match PathBuilder(*rest):
                case []:
                    await render_user_manage_active_requests_panel(
                        update=update,
                        context=context,
                        action=action,
                        base_path=root.add(action)
                    )
                    return PCS.USER_CONVERSATION

                case [request_id]:
                    if action == UserManageRequestsRoute.DETAILS:
                        await render_request_details_panel(
                            update=update,
                            context=context,
                            base_path=root.add(action, request_id),
                            ix=int(request_id)
                        )
                    elif action == UserManageRequestsRoute.CANCEL:
                        await render_confirm_cancel_panel(
                            update=update,
                            context=context,
                            base_path=root.add(action, request_id),
                            ix=int(request_id)
                        )
                    else:
                        await render_action_not_permitted_panel(
                            update=update,
                            context=context,
                            base_path=relative_path.back(2)
                        )
                        log.warning(f"User request management action not recognized ({update.effective_user.id}): "
                                    f"{PathBuilder(root.segments.append(action)).build()}")

                    return PCS.USER_CONVERSATION



    elif len(root) >= 3:
        if root[-3] == "cancel" and root[-1] == "yes":
            # path."endswith" [cancel, <ix>, yes]
            await cancel_request(context=context, ix=int(root[-2]))
            await render_request_cancelled_panel(update=update, context=context)

        elif root[2] in ("enable_notifications", "disable_notifications"):
            await toggle_status_notifications(context=context, ix=int(root[-2]))
            await render_request_details_panel(update=update, context=context, ix=int(root[1]))

    return PCS.USER_CONVERSATION
