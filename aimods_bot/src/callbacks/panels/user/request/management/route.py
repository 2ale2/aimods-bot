from telegram import Update

from aimods_bot.src.callbacks.panels.user.request.management.handle import cancel_request, toggle_status_notifications
from aimods_bot.src.callbacks.panels.user.request.management.render import \
    render_active_request_panel, render_user_request_management_panel, render_user_request_action_panel, \
    render_confirm_cancel_panel, render_request_details_panel, render_request_cancelled_panel, \
    render_user_request_archive_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def user_request_management_route(update: Update, context: CustomContext, path: list[str]):
    if len(path) == 0:
        await render_user_request_management_panel(update=update, context=context)
        return PCS.USER_CONVERSATION

    match path[0]:
        case "active_requests":
            return await user_request_action_route(update=update, context=context, path=path[1:])
        case "requests_archive":
            await render_user_request_archive_panel(
                update=update,
                context=context,
                user_id=None,
                requested_by_admin=False
            )
            return PCS.USER_CONVERSATION


async def user_request_action_route(
        update: Update,
        context: CustomContext,
        path: list[str]):
    if len(path) == 0:
        await render_active_request_panel(update=update, context=context)

    elif len(path) == 1:
        await render_user_request_action_panel(update=update, context=context, action=path[0])

    elif len(path) == 2:
        match path[0]:
            case "details":
                await render_request_details_panel(update=update, context=context, ix=int(path[1]))
            case "cancel":
                await render_confirm_cancel_panel(update=update, context=context, ix=int(path[1]))

    elif len(path) >= 3:
        if path[-3] == "cancel" and path[-1] == "yes":
            # path."endswith" [cancel, <ix>, yes]
            await cancel_request(context=context, ix=int(path[-2]))
            await render_request_cancelled_panel(update=update, context=context)

        elif path[2] in ("enable_notifications", "disable_notifications"):
            await toggle_status_notifications(context=context, ix=int(path[-2]))
            await render_request_details_panel(update=update, context=context, ix=int(path[1]))

    return PCS.USER_CONVERSATION
