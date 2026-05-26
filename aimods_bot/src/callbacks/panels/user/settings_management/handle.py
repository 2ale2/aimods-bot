from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import Platform, Category


async def handle_user_section_opening_notification_toggle(
        context: CustomContext,
        platform: Platform,
        category: Category
):
    settings = context.pydc.persistent.user_notifications.section_opening_notifications

    settings[platform][category] = not settings[platform][category]
