from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.sections_management.handle import \
    handle_request_section_toggle, handle_request_section_limit
from aimods_bot.src.callbacks.panels.admin.requests_management.sections_management.render import \
    render_admin_request_section_configure_panel, render_admin_request_section_configure_platform_panel, \
    render_admin_request_section_configure_category_panel, render_admin_request_section_toggle_panel, \
    render_admin_request_section_toggled_panel, render_admin_request_section_limit_panel, \
    render_admin_request_section_limit_confirmed_panel, render_admin_request_section_limit_confirm_panel
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.constants import Platform, Category
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.utils.request_utils import get_platform_categories


async def admin_request_section_configure_route(update: Update, context: CustomContext, path: list[str]):
    if len(path) == 0:
        await render_admin_request_section_configure_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    if len(path) == 1:
        # expected: (admin/manage_requests/manage_sections)/<platform>
        platform = Platform(path[0])
        await render_admin_request_section_configure_platform_panel(
            update=update,
            context=context,
            platform=platform
        )
        return PCS.ADMIN_CONVERSATION

    if len(path) == 2:
        # expected: (admin/manage_requests/manage_sections)/<platform>/<category>
        platform = Platform(path[0])
        category = get_platform_categories(platform)(path[1])
        await render_admin_request_section_configure_category_panel(
            update=update,
            context=context,
            platform=platform,
            category=category
        )
        return PCS.ADMIN_CONVERSATION

    if len(path) == 3:
        platform = Platform(path[0])
        category = get_platform_categories(platform)(path[1])
        match path[2]:
            case "limit":
                await render_admin_request_section_limit_panel(
                    update=update,
                    context=context,
                    platform=platform,
                    category=category
                )
                return PCS.ADMIN_CONVERSATION
            case _:  # open/close
                await render_admin_request_section_toggle_panel(
                    update=update,
                    context=context,
                    platform=platform,
                    category=category,
                    action=path[2]
                )
                return PCS.ADMIN_CONVERSATION

    if len(path) == 4:
        platform = Platform(path[0])
        category = get_platform_categories(platform)(path[1])
        if path[2] in ("open", "close") and path[3] == "yes":
            await handle_request_section_toggle(
                context=context,
                platform=platform,
                category=category,
                action=path[2]
            )
            await render_admin_request_section_toggled_panel(
                update=update,
                context=context,
                platform=platform,
                category=category,
                action=path[2]
            )
            return PCS.ADMIN_CONVERSATION

        if path[2] == "limit" and path[3].isnumeric():
            limit = int(path[3])
            config = getattr(getattr(context.pyd.configuration.settings.request, platform.value), category.value)
            assert isinstance(config, CategorySetting)

            if config.limit == limit or (config.limit is None and limit == 0):
                await render_admin_request_section_configure_category_panel(
                    update=update,
                    context=context,
                    platform=platform,
                    category=category
                )
            else:
                await render_admin_request_section_limit_confirm_panel(
                    update=update,
                    context=context,
                    platform=platform,
                    category=category,
                    limit=int(path[3])
                )
            return PCS.ADMIN_CONVERSATION

    if len(path) == 5:
        platform = Platform(path[0])
        category = get_platform_categories(platform)(path[1])
        if path[2] == "limit" and path[3].isnumeric() and path[4] == "yes":
            await handle_request_section_limit(
                context=context,
                platform=platform,
                category=category,
                limit=int(path[3])
            )
            await render_admin_request_section_limit_confirmed_panel(
                update=update,
                context=context,
                platform=platform,
                category=category,
                limit=int(path[3])
            )
            return PCS.ADMIN_CONVERSATION
