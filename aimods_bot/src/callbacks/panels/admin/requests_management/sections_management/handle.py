from typing import Literal

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.constants import Platform, Category


def handle_request_section_toggle(
        context: CustomContext,
        platform: Platform,
        category: Category,
        action: Literal["open", "close"]
):
    opening = action == "open"
    config = getattr(getattr(context.pyd.configuration.settings.request, platform.value), category.value)
    assert isinstance(config, CategorySetting)

    if opening and len(context.get_active_category_requests(platform=platform, category=category)) >= config.limit:
        config.limit = None

    config.toggle = opening


def handle_request_section_limit(
        context: CustomContext,
        platform: Platform,
        category: Category,
        limit: int
):
    config = getattr(getattr(context.pyd.configuration.settings.request, platform.value), category.value)
    config.limit = limit if limit != 0 else None

    if len(context.get_active_category_requests(platform=platform, category=category)) >= config.limit:
        config.toggle = False
