from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.sections_management.handle import \
    handle_request_section_toggle, handle_request_section_limit
from aimods_bot.src.callbacks.panels.admin.requests_management.sections_management.render import (
    render_admin_request_section_configure_panel, render_admin_request_section_configure_platform_panel,
    render_admin_request_section_configure_category_panel, render_admin_request_section_toggle_panel,
    render_admin_request_section_toggled_panel, render_admin_request_section_limit_panel,
    render_admin_request_section_limit_confirmed_panel, render_admin_request_section_limit_confirm_panel
)
from aimods_bot.src.helpers.constants.constants import Platform
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.scheduler import schedule_section_opening_check_for_user_notification
from aimods_bot.src.helpers.utils.telegram_utils import resolve_pl_cat, get_config


async def admin_request_section_configure_route(update: Update, context: CustomContext, path: list[str]):
    match path:
        case []:
            await render_admin_request_section_configure_panel(update=update, context=context)

        case [pl_str]:
            await render_admin_request_section_configure_platform_panel(
                update=update, context=context, platform=Platform(pl_str)
            )

        case [pl_str, cat_str]:
            pl, cat = resolve_pl_cat(pl_str, cat_str)
            await render_admin_request_section_configure_category_panel(
                update=update, context=context, platform=pl, category=cat
            )

        case [pl_str, cat_str, "limit"]:
            pl, cat = resolve_pl_cat(pl_str, cat_str)
            await render_admin_request_section_limit_panel(
                update=update, context=context, platform=pl, category=cat
            )

        case [pl_str, cat_str, action] if action in ("open", "close"):
            pl, cat = resolve_pl_cat(pl_str, cat_str)
            await render_admin_request_section_toggle_panel(
                update=update, context=context, platform=pl, category=cat, action=action
            )

        case [pl_str, cat_str, action, "yes"] if action in ("open", "close"):
            pl, cat = resolve_pl_cat(pl_str, cat_str)

            await handle_request_section_toggle(context=context, platform=pl, category=cat, action=action)

            if action == "open":
                await schedule_section_opening_check_for_user_notification(
                    context=context, section=f"{pl_str}:{cat_str}"
                )

            await render_admin_request_section_toggled_panel(
                update=update, context=context, platform=pl, category=cat, action=action
            )

        case [pl_str, cat_str, "limit", limit_str]:
            pl, cat = resolve_pl_cat(pl_str, cat_str)
            limit = int(limit_str)
            config = get_config(context=context, platform=pl, category=cat)

            # Se il limite è identico o è "nessun limite" (0) ed era già None, ricarica il pannello
            if config.limit == limit or (config.limit is None and limit == 0):
                await render_admin_request_section_configure_category_panel(
                    update=update, context=context, platform=pl, category=cat
                )
            else:
                await render_admin_request_section_limit_confirm_panel(
                    update=update, context=context, platform=pl, category=cat, limit=limit
                )

        case [pl_str, cat_str, "limit", limit_str, "yes"]:
            pl, cat = resolve_pl_cat(pl_str, cat_str)
            limit = int(limit_str)

            await handle_request_section_limit(context=context, platform=pl, category=cat, limit=limit)
            await render_admin_request_section_limit_confirmed_panel(
                update=update, context=context, platform=pl, category=cat, limit=limit
            )

    return PCS.ADMIN_CONVERSATION