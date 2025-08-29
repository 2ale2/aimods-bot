from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.callbacks.panels.admin.requests_management.render import render_admin_request_management_panel, \
    render_admin_active_requests_management_panel, render_admin_active_requests_category_selector_panel, \
    render_admin_active_requests_category_panel, render_admin_manage_request_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.models import Platform
from aimods_bot.src.helpers.utils.request_utils import get_platform_categories, get_request_by_id


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
            pass

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

    return await admin_manage_request_route(update=update, context=context, path=path[3:], ix=path[-1])


async def admin_manage_request_route(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        path: list[str],
        ix: str
):
    request = get_request_by_id(context=context, ix=ix)

    if len(path) == 0:
        await render_admin_manage_request_panel(
            update=update,
            context=context,
            ix=ix,
            request=request
        )
        return PCS.ADMIN_CONVERSATION

