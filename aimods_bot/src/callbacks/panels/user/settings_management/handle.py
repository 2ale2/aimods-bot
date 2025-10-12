from aimods_bot.src.core.customcontext import CustomContext


async def handle_user_section_opening_notification_toggle(context: CustomContext, data: str):
    pl, ca = data.split(":")
    settings = context.pydc.persistent.user_notifications.section_opening_notifications

    settings[pl][ca] = not settings[pl][ca]
