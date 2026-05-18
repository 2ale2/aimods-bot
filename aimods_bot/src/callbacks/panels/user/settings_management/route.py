from telegram import Update

from aimods_bot.src.callbacks.panels.user.settings_management.handle import \
    handle_user_section_opening_notification_toggle
from aimods_bot.src.callbacks.panels.user.settings_management.render import render_user_settings_management_panel, \
    render_user_notification_settings_management_panel, render_user_section_opening_notification_settings_panel, \
    render_section_opening_notification_disabled_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_paths.navigation import UserManageSettingsRoute, NotificationAction
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.models.routing import PathBuilder


async def user_settings_management_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    from_notification = NotificationAction.FROM_NOTIFICATION in (root + relative_path).segments

    match relative_path.segments:
        case []:
            await render_user_settings_management_panel(update=update, context=context, base_path=root)

        case [UserManageSettingsRoute.NOTIFICATIONS, *rest]:
            root.add(UserManageSettingsRoute.NOTIFICATIONS)
            match PathBuilder(*rest).segments:
                case []:
                    await render_user_notification_settings_management_panel(
                        update=update,
                        context=context,
                        base_path=root
                    )

                case [UserManageSettingsRoute.SECTION_OPENING_NOTIFICATIONS, *rest]:
                    root.add(UserManageSettingsRoute.SECTION_OPENING_NOTIFICATIONS)
                    match PathBuilder(*rest).segments:
                        case []:
                            await render_user_section_opening_notification_settings_panel(
                                update=update,
                                context=context,
                                base_path=root
                            )
                        case [selected_section]:
                            await handle_user_section_opening_notification_toggle(
                                context=context,
                                data=selected_section
                            )
                            if from_notification:
                                await render_section_opening_notification_disabled_panel(
                                    update=update,
                                    context=context,
                                    base_path=root,
                                    data=selected_section
                                )
                            else:
                                await render_user_section_opening_notification_settings_panel(
                                    update=update,
                                    context=context,
                                    base_path=root
                                )

    return PCS.USER_CONVERSATION
