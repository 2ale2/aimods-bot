from telegram import Update

from aimods_bot.src.callbacks.panels.admin.settings_management.handle import \
    handle_admin_new_requests_notification_toggle, handle_admin_section_closing_notification_toggle
from aimods_bot.src.callbacks.panels.admin.settings_management.render import render_admin_settings_management_panel, \
    render_admin_notification_settings_management_panel, render_admin_new_requests_notification_settings_panel, \
    render_new_requests_notification_disabled_panel, render_admin_section_closing_notification_settings_panel, \
    render_section_closure_notification_disabled_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def admin_settings_management_route(update: Update, context: CustomContext, path: list[str]):
    if len(path) == 0:
        await render_admin_settings_management_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    if path[0] == "notifications":
        # Impostazioni per le notifiche lato admin
        # expected: .../notifications
        if len(path) == 1:
            await render_admin_notification_settings_management_panel(update=update, context=context)

        if len(path) == 2:
            match path[1]:
                case "new_requests":
                    # Impostazioni notifiche per le nuove richieste
                    await render_admin_new_requests_notification_settings_panel(update=update, context=context)
                case "section_closing":
                    await render_admin_section_closing_notification_settings_panel(update=update, context=context)
        if len(path) >= 3:
            if path[1] == "new_requests":
                await handle_admin_new_requests_notification_toggle(context=context, data=path[2])
                if len(path) < 4:
                    await render_admin_new_requests_notification_settings_panel(update=update, context=context)
                elif path[3] == "from_notification":
                    await render_new_requests_notification_disabled_panel(update=update, context=context, data=path[2])
            if path[1] == "section_closing":
                await handle_admin_section_closing_notification_toggle(context=context, data=path[2])
                if len(path) < 4:
                    await render_admin_section_closing_notification_settings_panel(update=update, context=context)
                elif path[3] == "from_notification":
                    await render_section_closure_notification_disabled_panel(
                        update=update,
                        context=context,
                        data=path[2]
                    )
        return PCS.ADMIN_CONVERSATION
