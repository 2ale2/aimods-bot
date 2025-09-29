from typing import Literal

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.constants import Platform, Category
from aimods_bot.src.helpers.utils.file_utils import save_yaml_configuration


async def handle_request_section_toggle(
        context: CustomContext,
        platform: Platform,
        category: Category,
        action: Literal["open", "close"]
):
    opening = action == "open"
    config = getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)
    assert isinstance(config, CategorySetting)

    if opening and len(context.get_active_category_requests(platform=platform, category=category)) >= config.limit:
        config.limit = None

    config.toggle = opening

    await save_yaml_configuration(context=context)


async def handle_request_section_limit(
        context: CustomContext,
        platform: Platform,
        category: Category,
        limit: int
):
    config = getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)
    config.limit = limit if limit != 0 else None

    if config.limit is not None:
        if len(context.get_active_category_requests(platform=platform, category=category)) >= config.limit:
            config.toggle = False

    await save_yaml_configuration(context=context)


async def handle_remove_user_request_limitation(context: CustomContext, user_id: int, section: str):
    user_limitations = context.get_user_request_limitations(user_id=user_id)
    new_limitations = []

    for el in user_limitations:
        if el.section == section:
            continue
        new_limitations.append(el)

    context.set_user_request_limitations(user_id=user_id, limitations=new_limitations)
