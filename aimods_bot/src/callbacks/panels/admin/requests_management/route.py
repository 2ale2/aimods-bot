from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.handle import confirm_rejection
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import render_request_deleted_panel, \
    render_request_inactive_panel
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.route import route_admin_limit_user_request, \
    route_admin_manage_limitations
from aimods_bot.src.callbacks.panels.admin.requests_management.render import render_admin_request_management_panel, \
    render_admin_active_requests_management_panel, render_admin_active_requests_category_selector_panel, \
    render_admin_active_requests_category_panel, render_admin_manage_request_panel, \
    render_change_request_status_confirmation_panel, render_request_status_changed_panel, \
    render_admin_manage_request_remove_confirmation_panel, render_admin_manage_request_removed_panel, \
    render_admin_manage_request_change_status_panel, render_admin_reject_request_panel, \
    render_admin_confirm_rejection_panel, render_admin_rejection_confirmed_panel, \
    render_admin_user_requests_archive_panel, send_user_request_status_changed_notification, \
    render_last_ten_requests_platform_panel, render_last_ten_requests_category_panel, \
    render_last_ten_requests_section_panel
from aimods_bot.src.callbacks.panels.admin.requests_management.sections_management.route import \
    admin_request_section_configure_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import Platform, RequestStatus, RejectRequestReason
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.request_utils import get_platform_categories
from aimods_bot.src.helpers.utils.user_utils import user_is_banned

log = logger.getChild(__name__)


async def admin_requests_management_route(update: Update, context: CustomContext, path: list[str]):
    if len(path) == 0:
        await render_admin_request_management_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "active_requests":
            return await admin_active_requests_management_route(update=update, context=context, path=path[1:])
        case "manage_sections":
            return await admin_request_section_configure_route(update=update, context=context, path=path[1:])
        case "manage_limitations":
            if len(path) == 1:
                context.free_base_path()
                context.pydc.persistent.limiting_user_requests = None
            return await route_admin_manage_limitations(update=update, context=context, path=path[1:])
        case "user_requests_archive":
            await render_admin_user_requests_archive_panel(update=update, context=context)
            return PCS.SET_USER_FOR_REQUEST_ARCHIVE
        case "last_10":
            if len(path) == 1:
                await render_last_ten_requests_platform_panel(update=update, context=context)
            elif len(path) == 2:
                await render_last_ten_requests_category_panel(update=update, context=context, pl=Platform(path[-1]))
            else:  # len(path) == 3
                pl = Platform(path[-2])
                cats = get_platform_categories(platform=pl)
                await render_last_ten_requests_section_panel(update=update, context=context, pl=pl, ca=cats(path[-1]))
            return PCS.ADMIN_CONVERSATION


async def admin_active_requests_management_route(update: Update, context: CustomContext, path: list[str]):
    if update.callback_query and update.callback_query.data == context.pydc.persistent.base_path:
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

    if request is None:
        log.warning("Request variable is None. The request may have been deleted while managing it.")
        await render_request_deleted_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

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
            if not request.is_active:
                await render_request_inactive_panel(update=update, context=context)
                return PCS.ADMIN_CONVERSATION

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
            if not request.is_active:
                await render_request_inactive_panel(update=update, context=context)
                return PCS.ADMIN_CONVERSATION

            await render_admin_manage_request_change_status_panel(
                update=update,
                context=context,
                ix=ix,
                request=request
            )

        elif path[0] == "reject":
            if not request.is_active:
                await render_request_inactive_panel(update=update, context=context)
                return PCS.ADMIN_CONVERSATION
            context.pydc.ephemeral.rejecting = request
            context.pydc.persistent.bot_message_id = update.effective_message.id
            await render_admin_reject_request_panel(
                update=update,
                context=context,
                ix=ix,
                request=request
            )
            return PCS.SET_REQUEST_REJECTION_REASON

    elif len(path) == 2:
        if path[-2] in RequestStatus and path[-1] == "yes":
            if not request.is_active:
                await render_request_inactive_panel(update=update, context=context)
                return PCS.ADMIN_CONVERSATION

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

            user = update.effective_user
            if (not await user_is_banned(context=context, user_id=user.username or user.id) and
                    request.status_change_notifications and status == RequestStatus.COMPLETED):
                # Notifico l'utente
                await send_user_request_status_changed_notification(
                    update=update,
                    context=context,
                    user_id=request.user_id,
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

        elif path[-2] == "reject" and path[-1] in RejectRequestReason:
            if not request.is_active:
                await render_request_inactive_panel(update=update, context=context)
                return PCS.ADMIN_CONVERSATION

            await render_admin_confirm_rejection_panel(
                update=update,
                context=context,
                ix=ix,
                request=request,
                reason=path[-1]
            )

    elif len(path) == 3:
        if not request.is_active:
            await render_request_inactive_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION

        if path[-3] == "reject" and path[-1] == "yes":
            await confirm_rejection(context, ix=ix, reason=path[-2])
            await render_admin_rejection_confirmed_panel(
                update=update,
                context=context,
                ix=ix,
                request=request,
                reason=path[-2]
            )

            user = update.effective_user
            if not await user_is_banned(
                    context=context,
                    user_id=user.username or user.id
            ) and request.status_change_notifications:
                # Notifico l'utente
                await send_user_request_status_changed_notification(
                    update=update,
                    context=context,
                    user_id=request.user_id,
                    request=request
                )

    return PCS.ADMIN_CONVERSATION
