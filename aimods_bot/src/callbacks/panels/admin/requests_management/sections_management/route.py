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
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction, \
    LimitationsOp
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.scheduler import schedule_section_opening_check_for_user_notification
from aimods_bot.src.core.config_accessor import get_section_config


async def route_admin_request_section_configure_selection(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_admin_request_section_configure_panel(update=update, context=context, base_path=root)

        case [platform] if platform in Platform:
            await render_admin_request_section_configure_platform_panel(
                update=update, context=context, platform=platform, base_path=root.add(platform)
            )

        case [platform, category, *rest] if platform in Platform and category in Category:
            await admin_request_section_configure_route(
                update=update,
                context=context,
                section=RequestSection(platform=platform, category=category),
                root=root.add(platform, category),
                relative_path=PathBuilder(*rest)
            )

    return PCS.ADMIN_CONVERSATION


async def admin_request_section_configure_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        section: RequestSection
):
    match relative_path.segments:
        case []:
            await render_admin_request_section_configure_category_panel(
                update=update,
                context=context,
                section=section,
                base_path=root
            )

        case [LimitationsOp.LIMIT, *rest]:
            match PathBuilder(*rest).segments:
                case []:
                    await render_admin_request_section_limit_panel(
                        update=update,
                        context=context,
                        section=section,
                        base_path=root.add(LimitationsOp.LIMIT)
                    )

                case [limit_str]:
                    limit = int(limit_str)
                    config = get_section_config(context=context, section=section)

                    # Se il limite è identico o è "nessun limite" (0) ed era già None, ricarica il pannello
                    if config.limit == limit or (config.limit is None and limit == 0):
                        await render_admin_request_section_configure_category_panel(
                            update=update,
                            context=context,
                            base_path=root,
                            section=section
                        )
                    else:
                        await render_admin_request_section_limit_confirm_panel(
                            update=update,
                            context=context,
                            base_path=root.add(LimitationsOp.LIMIT, limit_str),
                            section=section,
                            limit=limit
                        )

                case [limit_str, GlobalAction.YES]:
                    limit = int(limit_str)

                    await handle_request_section_limit(
                        context=context,
                        section=section,
                        limit=limit
                    )
                    await render_admin_request_section_limit_confirmed_panel(
                        update=update,
                        context=context,
                        base_path=root.add(limit_str),
                        section=section,
                        limit=limit
                    )

        case [action, *rest] if action in (GlobalAction.OPEN, GlobalAction.CLOSE):
            match PathBuilder(*rest).segments:
                case []:
                    await render_admin_request_section_toggle_panel(
                        update=update,
                        context=context,
                        base_path=root.add(action),
                        section=section,
                        action=action
                    )

                case [GlobalAction.YES]:
                    await handle_request_section_toggle(
                        context=context,
                        section=section,
                        action=action
                    )

                    if action == GlobalAction.OPEN:
                        await schedule_section_opening_check_for_user_notification(
                            context=context,
                            section=section
                        )

                    await render_admin_request_section_toggled_panel(
                        update=update,
                        context=context,
                        base_path=root.add(action),
                        section=section,
                        action=action
                    )
