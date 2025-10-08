from aimods_bot.src.core.customcontext import CustomContext


async def handle_admin_new_requests_notification_toggle(context: CustomContext, data: str):
    pl, ca = data.split(":")
    settings = context.pydc.persistent.admin_notifications.new_requests_notifications

    settings[pl][ca] = not settings[pl][ca]
