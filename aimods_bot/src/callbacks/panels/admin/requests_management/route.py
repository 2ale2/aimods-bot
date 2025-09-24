from telegram import Update
from aimods_bot.src.core.customcontext import CustomContext

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.route import route_admin_limit_user_request
from aimods_bot.src.callbacks.panels.admin.requests_management.render import render_admin_request_management_panel, \
    render_admin_active_requests_management_panel, render_admin_active_requests_category_selector_panel, \
    render_admin_active_requests_category_panel, render_admin_manage_request_panel, \
    render_change_request_status_confirmation_panel, render_request_status_changed_panel, \
    render_admin_manage_request_remove_confirmation_panel, render_admin_manage_request_removed_panel, \
    render_admin_manage_request_change_status_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.constants import Platform, RequestStatus
from aimods_bot.src.helpers.utils.request_utils import get_platform_categories


async def admin_requests_management_route(update: Update, context: CustomContext, path: list[str]):
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


async def admin_active_requests_management_route(update: Update, context: CustomContext, path: list[str]):
    if update.callback_query and update.callback_query.data == context.pyd.base_path:
        #  Se la path è uguale a quella salvata, significa che sono tornato da una funzionalità secondaria
        #  NOTA - Potrei spostare il controllo dove mi aspetto che il flow ritorni, per ridurre le probabilità d'errore
        context.free_base_path()

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
        return await admin_manage_request_route(update=update, context=context, path=path[3:], ix=int(path[2]))


async def admin_manage_request_route(
        update: Update,
        context: CustomContext,
        path: list[str],
        ix: int
):
    request = context.get_active_request_by_id(ix=ix)

    if len(context.get_active_category_requests(platform=request.platform, category=request.category)) == 1:
        back_button_callback_key = "admin/manage_requests/active_requests"
    else:
        back_button_callback_key = None

    if len(path) == 0:
        # expected: (<platform>/<category>/<id>)
        await render_admin_manage_request_panel(
            update=update,
            context=context,
            ix=ix,
            request=request,
            back_button_callback_key=back_button_callback_key
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

        elif path[0] == "change_status":
            await render_admin_manage_request_change_status_panel(
                update=update,
                context=context,
                ix=ix,
                request=request
            )


    elif len(path) == 2:
        if path[-2] in RequestStatus and path[-1] == "yes":
            # expected: (<platform>/<category>/<id>)/<new_status>/yes
            status = RequestStatus(path[-2])
            await context.edit_request_status(ix=ix, status=status)
            request = context.get_active_request_by_id(ix=ix)

            await render_request_status_changed_panel(
                update=update,
                context=context,
                ix=ix,
                request=request
            )
        elif path[-2] == "remove" and path[-1] == "yes":
            # expected: (<platform>/<category>/<id>)/remove/yes
            context.remove_from_active_requests(ix=ix)
            await render_admin_manage_request_removed_panel(
                update=update,
                context=context,
                ix=ix
            )


    return PCS.ADMIN_CONVERSATION
