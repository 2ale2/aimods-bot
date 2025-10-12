from telegram import Update

from aimods_bot.src.callbacks.panels.user.settings_management.handle import \
    handle_user_section_opening_notification_toggle
from aimods_bot.src.callbacks.panels.user.settings_management.render import render_user_settings_management_panel, \
    render_user_notification_settings_management_panel, render_user_section_opening_notification_settings_panel, \
    render_section_opening_notification_disabled_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def user_settings_management_route(update: Update, context: CustomContext, path: list[str]):
    if len(path) == 0:
        await render_user_settings_management_panel(update=update, context=context)
        return PCS.USER_CONVERSATION

    if path[0] == "notifications":
        # Impostazioni per le notifiche lato user
        # expected: .../notifications
        if len(path) == 1:
            await render_user_notification_settings_management_panel(update=update, context=context)

        if len(path) == 2:
            match path[1]:
                case "section_opening":
                    # Impostazioni notifiche per l'apertura sezioni
                    await render_user_section_opening_notification_settings_panel(update=update, context=context)

        if len(path) >= 3:
            if path[1] == "section_opening":
                await handle_user_section_opening_notification_toggle(context=context, data=path[2])
                if len(path) < 4:
                    await render_user_section_opening_notification_settings_panel(update=update, context=context)
                elif path[3] == "from_notification":
                    await render_section_opening_notification_disabled_panel(update=update, context=context, data=path[2])
        return PCS.USER_CONVERSATION
