from telegram import Update

from aimods_bot.src.callbacks.panels.general.user_archive.route import route_user_archive
from aimods_bot.src.callbacks.panels.user.request.management.handle import cancel_request, toggle_status_notifications
from aimods_bot.src.callbacks.panels.user.request.management.render import \
    render_active_request_panel, render_user_request_management_panel, render_user_request_action_panel, \
    render_confirm_cancel_panel, render_request_details_panel, render_request_cancelled_panel, \
    render_user_request_archive_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_paths.navigation import UserViewRequestsRoute
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.models.routing import PathBuilder


async def user_request_management_route(update: Update, context: CustomContext, path: PathBuilder):
    if not len(path):
        await render_user_request_management_panel(update=update, context=context, base_path=path)
        return PCS.USER_CONVERSATION

    match path.segments:
        case [UserViewRequestsRoute.ACTIVE, *rest]:
            return await user_request_action_route(
                update=update,
                context=context,
                root=path.add(UserViewRequestsRoute.ACTIVE),
                relative_path=PathBuilder(*rest)
            )
        case [UserViewRequestsRoute.REQUEST_ARCHIVE, *rest]:
            await route_user_archive(
                update=update,
                context=context,
                root=path.add(UserViewRequestsRoute.REQUEST_ARCHIVE),
                relative_path=PathBuilder([])  # Misura di sicurezza: forzo [] per forzare il ramo corretto del router
            )
            return PCS.USER_CONVERSATION


async def user_request_action_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    if len(root) == 0:
        await render_active_request_panel(update=update, context=context)

    elif len(root) == 1:
        await render_user_request_action_panel(update=update, context=context, action=root[0])

    elif len(root) == 2:
        match root[0]:
            case "details":
                await render_request_details_panel(update=update, context=context, ix=int(root[1]))
            case "cancel":
                await render_confirm_cancel_panel(update=update, context=context, ix=int(root[1]))

    elif len(root) >= 3:
        if root[-3] == "cancel" and root[-1] == "yes":
            # path."endswith" [cancel, <ix>, yes]
            await cancel_request(context=context, ix=int(root[-2]))
            await render_request_cancelled_panel(update=update, context=context)

        elif root[2] in ("enable_notifications", "disable_notifications"):
            await toggle_status_notifications(context=context, ix=int(root[-2]))
            await render_request_details_panel(update=update, context=context, ix=int(root[1]))

    return PCS.USER_CONVERSATION
