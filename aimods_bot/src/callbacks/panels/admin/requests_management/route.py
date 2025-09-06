from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.route import route_admin_limit_user_request
from aimods_bot.src.callbacks.panels.admin.requests_management.render import render_admin_request_management_panel, \
    render_admin_active_requests_management_panel, render_admin_active_requests_category_selector_panel, \
    render_admin_active_requests_category_panel, render_admin_manage_request_panel, \
    render_change_request_status_confirmation_panel, render_request_status_changed_panel, \
    render_admin_manage_request_remove_confirmation_panel, render_admin_manage_request_removed_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.models import Platform, RequestStatus
from aimods_bot.src.helpers.utils.request_utils import get_platform_categories, get_request_by_id, edit_request_status, \
    remove_active_request


async def admin_requests_management_route(update: Update, context: ContextTypes.DEFAULT_TYPE, path: list[str]):
    if len(path) == 0:
        await render_admin_request_management_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "active_requests":
            await admin_active_requests_management_route(update=update, context=context, path=path[1:])
        case "manage_topics":
            pass
        case "limit_user_request":
            return await route_admin_limit_user_request(update=update, context=context, path=path[1:], user_id=None)

    return PCS.ADMIN_CONVERSATION


async def admin_active_requests_management_route(update: Update, context: ContextTypes.DEFAULT_TYPE, path: list[str]):
    if len(path) == 0:
        await render_admin_active_requests_management_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    if len(path) == 1:
        await render_admin_active_requests_category_selector_panel(
            update=update,
            context=context,
            platform=Platform(path[0])
        )
        return PCS.ADMIN_CONVERSATION

    if len(path) == 2:
        platform = Platform(path[0])
        await render_admin_active_requests_category_panel(
            update=update,
            context=context,
            platform=platform,
            category=get_platform_categories(platform=platform)(path[1])
        )
        return PCS.ADMIN_CONVERSATION

    if len(path) >= 3:
        # expected: <platform>/<category>/<id>/...
        return await admin_manage_request_route(update=update, context=context, path=path[3:], ix=path[2])


async def admin_manage_request_route(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        path: list[str],
        ix: str
):
    request = get_request_by_id(context=context, ix=ix)

    if len(path) == 0:
        # expected: (<platform>/<category>/<id>)
        await render_admin_manage_request_panel(
            update=update,
            context=context,
            ix=ix,
            request=request
        )

    elif len(path) == 1:
        if path[0] in RequestStatus and RequestStatus(path[0]) is not RequestStatus.REJECTED:
            # expected: (<platform>/<category>/<id>)/<new_status>
            await render_change_request_status_confirmation_panel(
                update=update,
                context=context,
                ix=ix,
                request=request,
                status=RequestStatus(path[-1])
            )
        elif path[0].startswith("limit"):
            # expected: (<platform>/<category>/<id>)/limit_<user_id>
            return await route_admin_limit_user_request(
                update=update,
                context=context,
                path=path[1:],
                user_id=int(path[0].split("_")[-1])
            )

        elif path[0] == "remove":
            # expected: (<platform>/<category>/<id>)/remove
            await render_admin_manage_request_remove_confirmation_panel(
                update=update,
                context=context,
                ix=ix,
                request=request
            )


    elif len(path) == 2:
        if path[-2] in RequestStatus and path[-1] == "yes":
            # expected: (<platform>/<category>/<id>)/<new_status>/yes
            status = RequestStatus(path[-2])
            await edit_request_status(context=context, ix=ix, status=status)
            request = get_request_by_id(context=context, ix=ix)

            await render_request_status_changed_panel(
                update=update,
                context=context,
                ix=ix,
                request=request
            )
        elif path[-2] == "remove" and path[-1] == "yes":
            # expected: (<platform>/<category>/<id>)/remove/yes
            remove_active_request(
                context=context,
                ix=ix
            )
            await render_admin_manage_request_removed_panel(
                update=update,
                context=context,
                ix=ix
            )


    return PCS.ADMIN_CONVERSATION
