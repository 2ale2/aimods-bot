from telegram import Update

from aimods_bot.src.callbacks.panels.admin.settings_management.handle import (
    handle_admin_new_requests_notification_toggle,
    handle_admin_section_closing_notification_toggle
)
from aimods_bot.src.callbacks.panels.admin.settings_management.render import (
    render_admin_settings_management_panel,
    render_admin_notification_settings_management_panel,
    render_admin_new_requests_notification_settings_panel,
    render_new_requests_notification_disabled_panel,
    render_admin_section_closing_notification_settings_panel,
    render_section_closure_notification_disabled_panel
)
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def admin_settings_management_route(update: Update, context: CustomContext, path: list[str]):
    match path:
        case []:
            await render_admin_settings_management_panel(update=update, context=context)

        case ["notifications"]:
            await render_admin_notification_settings_management_panel(update=update, context=context)

        # --- SEZIONE: NEW REQUESTS ---

        case ["notifications", "new_requests"]:
            await render_admin_new_requests_notification_settings_panel(update=update, context=context)

        case ["notifications", "new_requests", data]:
            await handle_admin_new_requests_notification_toggle(context=context, data=data)
            await render_admin_new_requests_notification_settings_panel(update=update, context=context)

        case ["notifications", "new_requests", data, "from_notification"]:
            await handle_admin_new_requests_notification_toggle(context=context, data=data)
            await render_new_requests_notification_disabled_panel(update=update, context=context, data=data)

        # --- SEZIONE: SECTION CLOSING ---

        case ["notifications", "section_closing"]:
            await render_admin_section_closing_notification_settings_panel(update=update, context=context)

        case ["notifications", "section_closing", data]:
            await handle_admin_section_closing_notification_toggle(context=context, data=data)
            await render_admin_section_closing_notification_settings_panel(update=update, context=context)

        case ["notifications", "section_closing", data, "from_notification"]:
            await handle_admin_section_closing_notification_toggle(context=context, data=data)
            await render_section_closure_notification_disabled_panel(update=update, context=context, data=data)

    return PCS.ADMIN_CONVERSATION