from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.handle import confirm_rejection
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import render_request_deleted_panel, \
    render_request_inactive_panel
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.route import route_admin_manage_limitations
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
    admin_request_section_configure_selection_route
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import Platform, RequestStatus, RejectRequestReason
from aimods_bot.src.helpers.constants.conversation_paths.navigation import AdminRequestsRoute, \
    AdminRequestManagementRoute
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.request_utils import get_platform_categories
from aimods_bot.src.helpers.utils.user_utils import user_is_banned

log = logger.getChild(__name__)


async def admin_requests_management_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_admin_request_management_panel(update=update, context=context, base_path=root)
            return PCS.ADMIN_CONVERSATION

        case [AdminRequestsRoute.ACTIVE, *rest]:
            return await admin_active_requests_management_route(
                update=update,
                context=context,
                root=root.add(AdminRequestsRoute.ACTIVE),
                relative_path=PathBuilder(*rest)
            )

        case [AdminRequestsRoute.MANAGE_SECTIONS, *rest]:
            return await admin_request_section_configure_selection_route(
                update=update,
                context=context,
                root=root.add(AdminRequestsRoute.MANAGE_SECTIONS),
                relative_path=PathBuilder(*rest)
            )

        case [AdminRequestsRoute.MANAGE_LIMITATIONS, *rest]:
            context.free_base_path()
            context.pydc.persistent.limiting_user_requests = None
            return await route_admin_manage_limitations(update=update, context=context, path=rest)

        case [AdminRequestsRoute.USER_REQUESTS_ARCHIVE, *rest]:
            await render_admin_user_requests_archive_panel(update=update, context=context)
            return PCS.SET_USER_FOR_REQUEST_ARCHIVE

        case [AdminRequestsRoute.LAST_10, *rest]:
            await render_last_ten_requests_platform_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION

        case ["last_10", platform_str]:
            await render_last_ten_requests_category_panel(
                update=update,
                context=context,
                pl=Platform(platform_str)
            )
            return PCS.ADMIN_CONVERSATION

        case ["last_10", platform_str, category_str]:
            pl = Platform(platform_str)
            cats = get_platform_categories(platform=pl)
            await render_last_ten_requests_section_panel(
                update=update,
                context=context,
                pl=pl,
                ca=cats(category_str)
            )
            return PCS.ADMIN_CONVERSATION

        case _:
            log.warning(f"Unhandled path in admin_requests_management: {relative_path}")
            return PCS.ADMIN_CONVERSATION


async def admin_active_requests_management_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    if update.callback_query and update.callback_query.data == context.pydc.persistent.base_path:
        #  Se la path è uguale a quella salvata, significa che sono tornato da una funzionalità secondaria
        #  NOTA - Potrei spostare il controllo dove mi aspetto che il flow ritorni, per ridurre le probabilità d'errore
        context.free_base_path()

    match relative_path.segments:
        case []:
            # ==== MENU PRINCIPALE - SCELTA CATEGORIA ====
            await render_admin_active_requests_management_panel(update=update, context=context, base_path=root)

        case [platform_str]:
            # ==== SCELTA PIATTAFORMA ====
            await render_admin_active_requests_category_selector_panel(
                update=update,
                context=context,
                root=root,
                platform=Platform(platform_str)
            )

        case [platform_str, category_str]:
            # ==== LISTA RICHIESTE ====
            platform = Platform(platform_str)
            cat_enum = get_platform_categories(platform=platform)

            await render_admin_active_requests_category_panel(
                update=update,
                context=context,
                platform=platform,
                category=cat_enum(category_str)
            )

        # ==== GESTIONE RICHIESTA ====
        case [platform_str, category_str, request_id_str, *sub_path]:
            if request_id_str.isdigit():
                return await admin_manage_request_route(
                    update=update,
                    context=context,
                    root=root.add(platform_str, category_str, request_id_str),
                    relative_path=PathBuilder(*sub_path),
                    ix=int(request_id_str)
                )
            else:
                log.warning(f"Invalid request ID received: {request_id_str}")

        case _:
            log.warning(f"Unhandled path structure in active requests: {relative_path}")

    return PCS.ADMIN_CONVERSATION


async def admin_manage_request_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        ix: int
):
    request = context.get_active_request_by_id(ix=ix)

    if request is None:
        log.warning("Request variable is None. The request may have been deleted while managing it.")
        await render_request_deleted_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    async def ensure_active():
        if not request.is_active:
            await render_request_inactive_panel(update=update, context=context)
            return False
        return True

    match relative_path.segments:
        case []:
            await render_admin_manage_request_panel(update=update, context=context, request=request)

        # --- LIMITI UTENTE ---
        case [AdminRequestManagementRoute.LIMIT, *rest]:
            user_id = int(rest[-1])
            return await route_admin_limit_user_request(
                update=update, context=context, path=rest, user_id=user_id
            )

        # --- REMOVE ---
        case ["remove"]:
            await render_admin_manage_request_remove_confirmation_panel(update, context, ix, request)

        case ["remove", "yes"]:
            context.remove_from_active_requests(ix=ix)
            await render_admin_manage_request_removed_panel(update, context, ix)

        # --- CHANGE STATUS ---
        case ["change_status"]:
            if await ensure_active():
                await render_admin_manage_request_change_status_panel(update, context, ix, request)

        # Conferma cambio stato
        case [status_str] if status_str in RequestStatus and RequestStatus(status_str) is not RequestStatus.REJECTED:
            if await ensure_active():
                await render_change_request_status_confirmation_panel(
                    update, context, ix, request, status=RequestStatus(status_str)
                )

        # Esecuzione cambio stato (es: "COMPLETED/yes")
        case [status_str, "yes"] if status_str in RequestStatus:
            if await ensure_active():
                new_status = RequestStatus(status_str)
                await context.edit_request_status(ix=ix, status=new_status)

                updated_request = context.get_active_request_by_id(ix=ix)
                await render_request_status_changed_panel(update, context, ix, request=updated_request)

                if new_status == RequestStatus.COMPLETED:
                    await _notify_user_safe(update, context, updated_request)

        # --- REJECT ---
        case ["reject"]:
            if await ensure_active():
                context.pydc.ephemeral.rejecting = request
                context.pydc.persistent.bot_message_id = update.effective_message.id
                await render_admin_reject_request_panel(
                    update=update,
                    context=context,
                    ix=ix,
                    request=request
                )
                return PCS.SET_REQUEST_REJECTION_REASON

        case ["reject", reason_str] if reason_str in RejectRequestReason:
            if await ensure_active():
                await render_admin_confirm_rejection_panel(
                    update, context, ix, request, reason=reason_str
                )

        case ["reject", reason_str, "yes"]:
            if await ensure_active():
                await confirm_rejection(context, ix=ix, reason=root[-2])
                await render_admin_rejection_confirmed_panel(
                    update=update,
                    context=context,
                    ix=ix,
                    request=request,
                    reason=root[-2]
                )
                await _notify_user_safe(update, context, request)

        case _:
            log.warning(f"Unhandled path in manage_request: {root}")

    return PCS.ADMIN_CONVERSATION


async def _notify_user_safe(update: Update, context: CustomContext, request):
    """Gestisce l'invio della notifica controllando ban e preferenze utente."""
    user = update.effective_user
    is_banned = await user_is_banned(context=context, user_id=user.username or user.id)

    if not is_banned and request.status_change_notifications:
        await send_user_request_status_changed_notification(
            update=update,
            context=context,
            user_id=request.user_id,
            request=request
        )
