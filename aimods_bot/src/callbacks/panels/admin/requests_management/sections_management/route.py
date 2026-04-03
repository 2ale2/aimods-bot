from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.sections_management.handle import \
    handle_request_section_toggle, handle_request_section_limit
from aimods_bot.src.callbacks.panels.admin.requests_management.sections_management.render import (
    render_admin_request_section_configure_panel, render_admin_request_section_configure_platform_panel,
    render_admin_request_section_configure_category_panel, render_admin_request_section_toggle_panel,
    render_admin_request_section_toggled_panel, render_admin_request_section_limit_panel,
    render_admin_request_section_limit_confirmed_panel, render_admin_request_section_limit_confirm_panel
)
from aimods_bot.src.helpers.constants.constants import Platform, Category
from aimods_bot.src.helpers.constants.conversation_paths.navigation import AdminRequestManagementRoute, GlobalAction
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.scheduler import schedule_section_opening_check_for_user_notification
from aimods_bot.src.helpers.utils.telegram_utils import resolve_pl_cat, get_config


async def admin_request_section_configure_selection_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_admin_request_section_configure_panel(update=update, context=context, base_path=root)

        case [pl_str]:
            await render_admin_request_section_configure_platform_panel(
                update=update, context=context, platform=Platform(pl_str), base_path=root.add(pl_str)
            )

        case [pl_str, cat_str, *rest]:
            pl, cat = resolve_pl_cat(pl_str, cat_str)
            await admin_request_section_configure_route(
                update=update,
                context=context,
                platform=pl,
                category=cat,
                root=root.add(pl_str, cat_str),
                relative_path=PathBuilder(*rest)
            )

    return PCS.ADMIN_CONVERSATION


async def admin_request_section_configure_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        platform: Platform,
        category: Category
):
    match relative_path.segments:
        case []:
            await render_admin_request_section_configure_category_panel(
                update=update,
                context=context,
                platform=platform,
                category=category,
                base_path=root
            )

        case [AdminRequestManagementRoute.LIMIT, *rest]:
            match PathBuilder(*rest).segments:
                case []:
                    await render_admin_request_section_limit_panel(
                        update=update,
                        context=context,
                        platform=platform,
                        category=category,
                        base_path=root.add(AdminRequestManagementRoute.LIMIT)
                    )

                case [limit_str]:
                    limit = int(limit_str)
                    config = get_config(context=context, platform=platform, category=category)

                    # Se il limite è identico o è "nessun limite" (0) ed era già None, ricarica il pannello
                    if config.limit == limit or (config.limit is None and limit == 0):
                        await render_admin_request_section_configure_category_panel(
                            update=update,
                            context=context,
                            base_path=root,
                            platform=platform,
                            category=category
                        )
                    else:
                        await render_admin_request_section_limit_confirm_panel(
                            update=update,
                            context=context,
                            base_path=root.add(AdminRequestManagementRoute.LIMIT, limit_str),
                            platform=platform,
                            category=category,
                            limit=limit
                        )

                case [limit_str, GlobalAction.YES]:
                    limit = int(limit_str)

                    await handle_request_section_limit(
                        context=context,
                        platform=platform,
                        category=category,
                        limit=limit
                    )
                    await render_admin_request_section_limit_confirmed_panel(
                        update=update,
                        context=context,
                        base_path=root.add(limit_str),
                        platform=platform,
                        category=category,
                        limit=limit
                    )

        case [action, *rest] if action in (GlobalAction.OPEN, GlobalAction.CLOSE):
            match PathBuilder(*rest).segments:
                case []:
                    await render_admin_request_section_toggle_panel(
                        update=update,
                        context=context,
                        base_path=root.add(action),
                        platform=platform,
                        category=category,
                        action=action
                    )

                case [GlobalAction.YES]:
                    await handle_request_section_toggle(
                        context=context,
                        platform=platform,
                        category=category,
                        action=action
                    )

                    if action == GlobalAction.OPEN:
                        await schedule_section_opening_check_for_user_notification(
                            context=context, section=f"{platform.value}:{category.value}"
                        )

                    await render_admin_request_section_toggled_panel(
                        update=update,
                        context=context,
                        base_path=root.add(action),
                        platform=platform,
                        category=category,
                        action=action
                    )
