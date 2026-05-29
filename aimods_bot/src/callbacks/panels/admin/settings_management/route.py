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
from aimods_bot.src.helpers.constants.conversation_paths.navigation import AdminSettingsRoute, NotificationAction, \
    AdminSettingsNotificationsRoute
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.models.routing import PathBuilder


async def admin_settings_management_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_admin_settings_management_panel(update=update, context=context, base_path=root)

        case [AdminSettingsRoute.NOTIFICATIONS, *sub_path]:
            await admin_notification_settings_management_route(
                update=update,
                context=context,
                root=root.add(AdminSettingsRoute.NOTIFICATIONS),
                relative_path=PathBuilder(*sub_path)
            )

    return PCS.ADMIN_CONVERSATION


# --- SEZIONE: ADMIN NOTIFICATIONS SETTINGS ---
async def admin_notification_settings_management_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_admin_notification_settings_management_panel(update=update, context=context, base_path=root)

        case [AdminSettingsNotificationsRoute.NEW_REQUESTS, *sub_path]:
            await admin_new_requests_notification_settings_management_route(
                update=update,
                context=context,
                root=root.add(AdminSettingsNotificationsRoute.NEW_REQUESTS),
                relative_path=PathBuilder(*sub_path)
            )

        case [AdminSettingsNotificationsRoute.SECTION_CLOSING, *sub_path]:
            await admin_closing_section_notification_settings_management_route(
                update=update,
                context=context,
                root=root.add(AdminSettingsNotificationsRoute.SECTION_CLOSING),
                relative_path=PathBuilder(*sub_path)
            )

    return PCS.ADMIN_CONVERSATION


# --- SEZIONE: ADMIN NEW REQUESTS NOTIFICATIONS SETTINGS ---
async def admin_new_requests_notification_settings_management_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    from_notification = NotificationAction.FROM_NOTIFICATION in (root + relative_path).segments

    match relative_path.segments:
        case []:
            await render_admin_new_requests_notification_settings_panel(update=update, context=context, base_path=root)

        case [data]:
            if from_notification:
                await handle_admin_new_requests_notification_toggle(context=context, data=data)
                await render_new_requests_notification_disabled_panel(update=update, context=context, data=data)
            else:
                await handle_admin_new_requests_notification_toggle(context=context, data=data)
                await render_admin_new_requests_notification_settings_panel(
                    update=update,
                    context=context,
                    base_path=root
                )

    return PCS.ADMIN_CONVERSATION


# --- SEZIONE: ADMIN SECTION CLOSING NOTIFICATIONS SETTINGS ---
async def admin_closing_section_notification_settings_management_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_admin_section_closing_notification_settings_panel(
                update=update,
                context=context,
                base_path=root
            )

        case [data]:
            await handle_admin_section_closing_notification_toggle(context=context, data=data)
            await render_admin_section_closing_notification_settings_panel(
                update=update,
                context=context,
                base_path=root
            )

        case [data, NotificationAction.FROM_NOTIFICATION]:
            await handle_admin_section_closing_notification_toggle(context=context, data=data)
            await render_section_closure_notification_disabled_panel(update=update, context=context, data=data)

    return PCS.ADMIN_CONVERSATION
